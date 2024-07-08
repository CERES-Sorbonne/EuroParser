import hashlib
import json
import logging
import concurrent.futures
import re
from collections import Counter
from typing import Optional, Any, Union

from bs4 import BeautifulSoup, element
from tqdm.auto import tqdm

from .models import FileToTransform, Pivot, Params
from .transformers.transformer import Transformer
from .utils import find_datetime
from .daniel_light import get_KW
from .lang_detect import detect_lang


class BadArticle(Exception):
    pass


class PivotTransformer(Transformer):
    journal_split = re.compile(r"\(| -|,? no. | \d|  | ;|\.fr")
    double_spaces_and_beyond = re.compile(r"(\s{2,})")
    def __init__(self, params: Optional[Params] = None, **kwargs: Optional[Any]) -> None:
        super().__init__(params, **kwargs)
        self.corpus = []
        self.bad_articles = []
        self.ids = set()
        self.all_keywords = Counter()

    def subspaces(self, s: str) -> str:
        return self.double_spaces_and_beyond.sub(r"\1", s).strip()

    def transform(self, files_to_transform: list[FileToTransform]) -> list[Pivot]:
        for file in files_to_transform:
            self._logger.debug("Processing file " + file.name)
            soup = BeautifulSoup(file.file, 'lxml')
            articles = soup.find_all("article")

            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [executor.submit(self.transform_article, article) for article in articles]
                concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)

        self._logger.info(f"Nombre d'articles : {len(self.corpus)}")

        self.persist_json()
        self.apply_parameters()

        return sorted(self.corpus, key=lambda x: x.epoch)

    def transform_article(self, article: Union[BeautifulSoup, element.Tag]) -> None:
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
                doc_sub_section = article.find("span", attrs={"class": "DocTitreSousSection"}).find_next_sibling("span").text
            except AttributeError:
                doc_sub_section = ""

            try:
                datetime = find_datetime(doc_header or doc_sub_section)
            except ValueError:
                raise BadArticle("datetime")

            if datetime:
                doc.update({
                    "date": datetime.strftime("%Y %m %dT%H:%M:%S"),
                    "annee": datetime.year,
                    "mois": datetime.month,
                    "jour": datetime.day,
                    "heure": datetime.hour,
                    "minute": datetime.minute,
                    "seconde": datetime.second,
                    "epoch": datetime.timestamp()
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


            doc["texte"] = self.subspaces(doc_text.text.strip())

            doc_auteur = doc_titre_full.find_next_sibling('p')

            if doc_auteur and "class" in doc_auteur.attrs and doc_auteur.attrs['class'] == ['sm-margin-bottomNews']:
                doc["auteur"] = self.subspaces(doc_auteur.text.strip().lower())

            # on garde uniquement le titre (sans les fioritures)
            journal_clean = self.journal_split.split(doc["journal"])[0]
            doc["journal_clean"] = self.subspaces(journal_clean)

            doc["keywords"] = get_KW(doc["titre"], doc["texte"])

            self.all_keywords.update(doc["keywords"])

            identifiant = ' '.join([doc["titre"], doc["journal_clean"], doc["date"]])

            langue = detect_lang(doc["texte"])
            if langue:
                doc["langue"] = langue

            if identifiant not in self.ids:
                doc["identifiant"] = hashlib.sha256(identifiant.encode()).hexdigest()
                self.corpus.append(Pivot(**doc))
                self.ids.add(identifiant)

        except BadArticle as e:
            if self._logger.isEnabledFor(logging.DEBUG):
                self._add_error(e, article)
                self.bad_articles.append(article)

        return

    def apply_parameters(self) -> list[Pivot]:
        if self.params.filter_keywords is True:
            for article in self.corpus:
                article.keywords = list(filter(self.filter_kw, article.keywords))

        return self.corpus

    def filter_kw(self, keyword: str) -> bool:
        return self.all_keywords[keyword] > 1

    def get_bad_articles(self) -> None:
        print(self.bad_articles)

    def persist_json(self) -> None:
        """
        utility function to persist the result of the pivot transformation
        """
        if not self.output_path:
            return

        json_ver = json.dumps({i: article.dict() for i, article in enumerate(self.corpus)}, ensure_ascii=False)
        # hash_json = hashlib.sha256(json_ver.encode()).hexdigest()
        # with (self.output_path / f"{hash_json}.json").open("w", encoding="utf-8") as f:
        output_file = self.output_path / f"{hashlib.sha256(json_ver.encode()).hexdigest()}.json"

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
