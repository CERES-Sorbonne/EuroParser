import hashlib
import json
import logging
import os
import concurrent.futures

from pathlib import Path

from bs4 import BeautifulSoup

from tqdm.auto import tqdm

from europarser.models import FileToTransform, Pivot, TransformerOutput, Params
from europarser.transformers.transformer import Transformer
from europarser.utils import find_date, find_datetime
import re
from europarser.daniel_light import get_KW
from europarser.lang_detect import detect_lang


class BadArticle(Exception):
    pass


class PivotTransformer(Transformer):
    def __init__(self, params: Params = Params()):
        super().__init__()
        self.corpus = []
        self.bad_articles = []
        self.ids = set()
        self.all_keywords = {}
        self.params = params

    def transform(self, files_to_transform: list[FileToTransform]) -> list[Pivot]:
        for file in files_to_transform:
            self._logger.debug("Processing file " + file.name)
            soup = BeautifulSoup(file.file, 'lxml')
            articles = soup.find_all("article")

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(self.transform_article, article) for article in articles]
                concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)


        print("Nombre d'articles : ", len(self.corpus))

        self.persist_json()
        self.apply_parameters()

        return sorted(self.corpus, key=lambda x: x.epoch)

    def transform_article(self, article):
        try:
            doc = {
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
            }
            try:
                doc["journal"] = article.find("span", attrs={"class": "DocPublicationName"}).text.strip()
            except Exception as e:
                self._logger.debug("pas un article de presse")
                raise BadArticle("journal")

            try:
                doc_header = article.find("span", attrs={"class": "DocHeader"}).text.strip()
            except AttributeError:
                doc_header = ""

            try:
                doc_sub_section = article.find("span", attrs={"class": "DocTitreSousSection"}).find_next_sibling("span").text.strip()
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
                    "class": "sm-margin-TopNews titreArticleVisu rdp__articletitle"}).text.strip()
            except AttributeError:
                try:
                    doc["titre"] = doc_titre_full.find("div", attrs={"class": "titreArticleVisu"}).text.strip()
                except AttributeError:
                    try:
                        doc["titre"] = doc_titre_full.text.strip()
                    except AttributeError:
                        raise BadArticle("titre")

            try:
                doc_bottomNews = doc_titre_full.find("p", attrs={"class": "sm-margin-bottomNews"}).text.strip()
                if not doc_bottomNews:
                    raise AttributeError
            except AttributeError:
                doc_bottomNews = ""

            try:
                doc_subtitle = doc_titre_full.find("p", attrs={"class": "sm-margin-TopNews rdp__subtitle"}).text.strip()
                if not doc_subtitle:
                    raise AttributeError
            except AttributeError:
                doc_subtitle = ""

            doc["complement"] = " | ".join((doc_header, doc_sub_section, doc_bottomNews, doc_subtitle))

            try:
                doc["texte"] = article.find("div", attrs={"class": "docOcurrContainer"}).text.strip()
            except AttributeError:
                if article.find("div", attrs={"class": "DocText clearfix"}) is None:
                    raise BadArticle("texte")
                else:
                    doc["texte"] = article.find("div", attrs={"class": "DocText clearfix"}).text.strip()

            doc_auteur = doc_titre_full.find_next_sibling('p')

            if doc_auteur and "class" in doc_auteur.attrs and doc_auteur.attrs['class'] == ['sm-margin-bottomNews']:
                doc["auteur"] = doc_auteur.text.strip().lower()

            # on garde uniquement le titre (sans les fioritures)
            journal_clean = re.split(r"\(| -|,? no. | \d|  | ;|\.fr", doc["journal"])[0]
            doc["journal_clean"] = journal_clean.strip()

            doc["keywords"] = get_KW(doc["titre"], doc["texte"])

            # TODO : use collections.Counter
            for kw in doc["keywords"]:
                self.all_keywords[kw] = self.all_keywords.get(kw, 0) + 1

            id_ = ' '.join([doc["titre"], doc["journal_clean"], doc["date"]])

            langue = detect_lang(doc["texte"])
            if langue:
                doc["langue"] = langue

            if id_ not in self.ids:
                self.corpus.append(Pivot(**doc))
                self.ids.add(id_)

        except BadArticle as e:
            if self._logger.isEnabledFor(logging.DEBUG):
                self._add_error(e, article)
                self.bad_articles.append(article)

        return

    def apply_parameters(self):
        if self.params.filter_keywords is True:
            for article in self.corpus:
                article.keywords = list(filter(self.filter_kw, article.keywords))

        return self.corpus

    def filter_kw(self, keyword):
        return self.all_keywords[keyword] > 1

    def get_bad_articles(self):
        print(self.bad_articles)

    def persist_json(self):
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
