import sys

# if sys.version_info < (3, 9):
#     from __future__ import annotations

from typing import List
from bs4 import BeautifulSoup
from datetime import date
import cchardet

from tqdm.auto import tqdm

from europarser.models import FileToTransform, Pivot
from europarser.transformers.transformer import Transformer
from europarser.utils import find_date, find_datetime
import re
from europarser.daniel_light import get_KW
from europarser.lang_detect import detect_lang


class BadArticle(Exception):
    pass


class PivotTransformer(Transformer):
    def __init__(self):
        super().__init__()
        self.corpus = None
        self.bad_articles = None

    def transform(self, file_to_transform: FileToTransform) -> List[Pivot]:
        self._logger.debug("Processing file " + file_to_transform.name)
        soup = BeautifulSoup(file_to_transform.file, 'lxml')

        self.corpus = []
        articles = soup.find_all("article")
        self.bad_articles = []
        ids = set()
        for article in articles:
            try:
                doc = {}
                try:
                    doc["journal"] = article.find("span", attrs={"class": "DocPublicationName"}).text.strip()
                except Exception as e:
                    self._logger.debug("pas un article de presse")
                    self._add_error(e, article)
                    raise BadArticle("journal")

                doc_header = article.find("span", attrs={"class": "DocHeader"})
                doc_header = doc_header.text.strip() if doc_header else ""

                doc_sub_section = article.find("span", attrs={"class": "DocTitreSousSection"})
                doc_sub_section = doc_sub_section.find_next_sibling("span").text.strip() if doc_sub_section else ""

                try:
                    datetime = find_datetime(doc_header or doc_sub_section)
                except ValueError:
                    raise BadArticle("datetime")

                if datetime:
                    doc["date"] = datetime.strftime("%Y %m %dT%H:%M:%S")
                    doc["annee"] = datetime.year
                    doc["mois"] = datetime.month
                    doc["jour"] = datetime.day
                    doc["heure"] = datetime.hour
                    doc["minute"] = datetime.minute
                    doc["seconde"] = datetime.second
                    doc["epoch"] = datetime.timestamp()
                else:
                    doc["date"] = None
                    doc["annee"] = None
                    doc["mois"] = None
                    doc["jour"] = None
                    doc["heure"] = None
                    doc["minute"] = None
                    doc["seconde"] = None
                    doc["epoch"] = None

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

                doc_bottomNews = doc_titre_full.find("p", attrs={"class": "sm-margin-bottomNews"})
                doc_bottomNews = doc_bottomNews.text.strip() if doc_bottomNews else ""

                doc_subtitle = doc_titre_full.find("p", attrs={"class": "sm-margin-TopNews rdp__subtitle"})
                doc_subtitle = doc_subtitle.text.strip() if doc_subtitle else ""

                doc["complement"] = " | ".join((doc_header, doc_sub_section, doc_bottomNews, doc_subtitle))

                try:
                    doc["texte"] = article.find("div", attrs={"class": "docOcurrContainer"}).text.strip()
                except AttributeError:
                    if article.find("div", attrs={"class": "DocText clearfix"}) is None:
                        continue
                    else:
                        doc["texte"] = article.find("div", attrs={"class": "DocText clearfix"}).text.strip()

                doc_auteur = doc_titre_full.find_next_sibling('p')

                if doc_auteur and "class" in doc_auteur.attrs and doc_auteur.attrs['class'] == ['sm-margin-bottomNews']:
                    doc["auteur"] = doc_auteur.text.strip().lower()

                else:
                    doc["auteur"] = "Unknown"

                # on garde uniquement le titre (sans les fioritures)
                journal_clean = re.split(r"\(| -|,? no. | \d|  | ;|\.fr", doc["journal"])[0]
                doc["journal_clean"] = journal_clean

                doc["keywords"] = ", ".join([x.lower() for x in get_KW(doc["titre"], doc["texte"])])

                id_ = ' '.join([doc["titre"], doc["journal_clean"], doc["date"]])

                langue = detect_lang(doc["texte"])
                doc["langue"] = langue if langue else "UNK"

                if id_ not in ids:
                    self.corpus.append(Pivot(**doc))
                    ids.add(id_)

            except BadArticle as e:
                self._add_error(e, article)
                self.bad_articles.append(article)

        return self.corpus


    def get_bad_articles(self):
        print(self.bad_articles)

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


