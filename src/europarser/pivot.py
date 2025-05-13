import concurrent.futures
import json
import logging
import re
from io import StringIO
from datetime import datetime
from collections import Counter
from hashlib import sha256
from typing import Optional, Any, Union

from bs4 import BeautifulSoup, element, Tag
from tqdm.auto import tqdm

from .daniel_light import get_KW
from .lang_detect import detect_lang
from .models import FileToTransform, Pivot, Params
from .transformers.transformer import Transformer
from .utils import find_datetime


class BadArticle(Exception):
    pass


class PivotTransformer(Transformer):
    journal_split = re.compile(r"\(| -|,? no. | \d|  | ;|\.fr")
    double_spaces_and_beyond = re.compile(r"(\s{2,})")

    def __init__(self, params: Optional[Params] = None, **kwargs: Optional[Any]) -> None:
        super().__init__(params, **kwargs)
        self._logger.setLevel(logging.DEBUG)
        self.corpus = []
        self.bad_articles = []
        self.ids = set()
        self.all_keywords = Counter()
        self.doublons_count = 0
        self.articles_count = 0
        self.good_articles_count = 0

    def clean_name(self, doc):
        return f"{doc.year}_{doc.month}_{doc.day}_{doc.journal}_{self.clean_string(doc.titre)[:50]}"

    def subspaces(self, s: str) -> str:
        return self.double_spaces_and_beyond.sub(r"\1", s).strip()

    def to_text_with_p(self, doc_text: Tag) -> str:
        """
        Utility function to convert a bs4 Tag to text, keeping the <p> tags
        :param doc_text: bs4 Tag
        :return: str
        """
        if not isinstance(doc_text, Tag):
            raise ValueError("doc_text is not a bs4 Tag")
        
        if not self.params.keep_p_tags:
            return self.subspaces(doc_text.text.strip())

        content = doc_text.contents
        if not content:
            return ""

        sio = StringIO()
        for e in content:
            if isinstance(e, str):
                sio.write(e.strip())
            elif isinstance(e, Tag):
                if e.name == "p":
                    sio.write(f"<p>{e.text.strip()}</p>")
                else:
                    sio.write(e.text.strip())
            else:
                raise ValueError(f"Unknown type {type(e)} in doc_text")

        return self.subspaces(sio.getvalue())



    def transform(self, files_to_transform: list[FileToTransform]) -> list[Pivot]:
        for file in files_to_transform:
            self._logger.debug("Processing file " + file.name)
            soup = BeautifulSoup(file.file, 'lxml')
            articles = soup.find_all("article")

            self.articles_count += len(articles)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(self.transform_article, article) for article in articles]
                concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)

        self._logger.info(f"Nombre d'articles : {len(self.corpus)}")

        self.persist_json()
        self._persist_errors(datetime.now().strftime("%Y%m%d"))
        self.apply_parameters()

        if self.doublons_count:
            self._logger.warn(f"Nombre d'articles doublons : {self.doublons_count}")
        else:
            self._logger.info("Pas d'articles doublons")

        self._logger.info(f"Nombre d'articles traités : {self.good_articles_count}")
        self._logger.info(f"Nombre d'articles au total : {self.articles_count}")

        return sorted(self.corpus, key=lambda x: x.epoch)

    def transform_article(
            self,
            article: Union[BeautifulSoup, element.Tag],
    ) -> None:
        assert isinstance(article, (BeautifulSoup, element.Tag)), "article is not a BeautifulSoup object"
        try:
            doc = {
                "identifiant": None,
                "journal": None,
                "date": None,
                "annee": None,
                "mois": None,
                "jour": None,
                "heure": None,
                "minute": None,
                "seconde": None,
                "epoch": None,
                "titre": None,
                "complement": None,
                "texte": None,
                "auteur": "Unknown",
                "journal_clean": None,
                "keywords": None,
                "langue": "UNK",
                "url": None,
            }
            try:
                doc["journal"] = self.subspaces(article.find("span", attrs={"class": "DocPublicationName"}).text)
            except Exception as e:
                self._logger.debug("pas un article de presse")
                raise BadArticle("journal")

            try:
                doc_header = article.find("span", attrs={"class": "DocHeader"}).text
            except AttributeError:
                doc_header = ""

            try:
                doc_sub_section = article.find(
                    "span",
                    attrs={"class": "DocTitreSousSection"}
                ).find_next_sibling("span").text
            except AttributeError:
                doc_sub_section = ""

            try:
                datetime_ = find_datetime(doc_header or doc_sub_section)
            except ValueError:
                raise BadArticle("datetime")

            if datetime_:
                doc.update({
                    "date": datetime_.strftime("%Y %m %dT%H:%M:%S"),
                    "annee": datetime_.year,
                    "mois": datetime_.month,
                    "jour": datetime_.day,
                    "heure": datetime_.hour,
                    "minute": datetime_.minute,
                    "seconde": datetime_.second,
                    "epoch": datetime_.timestamp()
                })

            try:
                doc_titre_full = article.find("div", attrs={"class": "titreArticle"})
                assert doc_titre_full is not None
            except AssertionError:
                try:
                    doc_titre_full = article.find("p", attrs={"class": "titreArticleVisu"})
                    assert doc_titre_full is not None
                except AssertionError:
                    raise BadArticle("titre")

            try:
                doc["titre"] = doc_titre_full.find("p", attrs={
                    "class": "sm-margin-TopNews titreArticleVisu rdp__articletitle"}).text
            except AttributeError:
                try:
                    doc["titre"] = doc_titre_full.find("div", attrs={"class": "titreArticleVisu"}).text
                except AttributeError:
                    try:
                        doc["titre"] = doc_titre_full.text
                    except AttributeError:
                        raise BadArticle("titre")

            doc["titre"] = self.subspaces(doc["titre"])

            try:
                doc_bottomNews = doc_titre_full.find("p", attrs={"class": "sm-margin-bottomNews"}).text
                if not doc_bottomNews:
                    raise AttributeError
            except AttributeError:
                doc_bottomNews = ""

            try:
                doc_subtitle = doc_titre_full.find("p", attrs={"class": "sm-margin-TopNews rdp__subtitle"}).text
                if not doc_subtitle:
                    raise AttributeError
            except AttributeError:
                doc_subtitle = ""

            doc["complement"] = self.subspaces(
                " | ".join((doc_header, doc_sub_section, doc_bottomNews, doc_subtitle))
            )

            try:
                doc_text = article.find("div", attrs={"class": "docOcurrContainer"})
                assert doc_text is not None and doc_text.text.strip()
            except AssertionError:
                if article.find("div", attrs={"class": "DocText clearfix"}) is None:
                    raise BadArticle("texte")
                else:
                    doc_text = article.find("div", attrs={"class": "DocText clearfix"})

            doc["url"] = ""
            for u in doc_text.select("a"):
                if "Cet article est paru dans" in u.get_text():
                    doc["url"] = u.get("href")
                    break

            doc["texte"] = self.to_text_with_p(doc_text)

            doc_auteur = doc_titre_full.find_next_sibling('p')

            if doc_auteur and "class" in doc_auteur.attrs and doc_auteur.attrs['class'] == ['sm-margin-bottomNews']:
                doc["auteur"] = self.subspaces(doc_auteur.text.strip().lower())

            # on garde uniquement le titre (sans les fioritures)
            journal_clean = self.journal_split.split(doc["journal"])[0]
            doc["journal_clean"] = self.subspaces(journal_clean)

            doc["keywords"] = get_KW(doc["titre"], doc["texte"])

            self.all_keywords.update(doc["keywords"])

            identifiant = sha256(
                ' '.join(
                    (doc["titre"], doc["journal"], doc["date"])
                ).encode()).hexdigest()

            langue = detect_lang(doc["texte"])
            if langue:
                doc["langue"] = langue

            if identifiant not in self.ids:
                doc["identifiant"] = identifiant
                self.corpus.append(Pivot(**doc))
                self.ids.add(identifiant)
            else:
                self._logger.warn(
                    "Article déjà présent dans le corpus : "
                    f"{doc['titre'] = }, {doc['date'] = }, {doc['journal'] = }, {identifiant = }"
                )
                self._add_error(ValueError("Article déjà présent dans le corpus"), article)
                self.doublons_count += 1

            self.good_articles_count += 1

        except BadArticle as e:
            if self._logger.isEnabledFor(logging.DEBUG):
                self._add_error(e, article)
                self.bad_articles.append(article)

        # To avoid the exception to be lost when catched by the ThreadPoolExecutor
        except Exception as e:
            print(e)
            raise e

        return

    def apply_parameters(self) -> list[Pivot]:
        if self.params.filter_keywords is True:
            for article in self.corpus:
                article.keywords = list(filter(lambda kw: self.filter_kw(kw, self.params.minimal_support_kw or 1), article.keywords))

        return self.corpus

    def filter_kw(self, keyword: str, minimum_shared_kw: int = 1) -> bool:
        return self.all_keywords[keyword] > minimum_shared_kw

    def get_bad_articles(self) -> None:
        print(self.bad_articles)

    def persist_json(self) -> None:
        """
        utility function to persist the result of the pivot transformation
        """
        if not self.output_path:
            return

        json_ver = json.dumps({i: article.dict() for i, article in enumerate(self.corpus)}, ensure_ascii=False)

        output_file = self.output_path / f"{sha256(json_ver.encode()).hexdigest()}.json"

        with output_file.open("w", encoding="utf-8") as f:
            f.write(json_ver)


if __name__ == "__main__":
    import cProfile
    import pstats

    from pathlib import Path

    pr = cProfile.Profile()
    pr.enable()

    p = PivotTransformer()

    for file in tqdm(list(Path("/home/marceau/Nextcloud/eurocollectes").glob("**/*.HTML"))):
        with file.open(mode="r", encoding="utf-8") as f:
            p.transform(FileToTransform(file=f.read(), name=file.name))

    p.get_bad_articles()

    pr.disable()
    ps = pstats.Stats(pr).sort_stats('cumulative')
    ps.print_stats()
