import sys

# if sys.version_info < (3, 9):
#     from __future__ import annotations

from typing import List
from bs4 import BeautifulSoup
from datetime import date

from europarser.models import FileToTransform, Pivot
from europarser.transformers.transformer import Transformer
from europarser.utils import find_date, find_datetime
import re
from europarser.daniel_light import get_KW
from europarser.lang_detect import detect_lang


class PivotTransformer(Transformer):
    def __init__(self):
        super().__init__()

    def transform(self, file_to_transform: FileToTransform) -> List[Pivot]:
        self._logger.warning("Processing file " + file_to_transform.name)
        soup = BeautifulSoup(file_to_transform.file, 'html.parser')

        corpus = []

        articles = soup.find_all("article")
        ids = set()
        for article in articles:
            doc = {}
            try:
                doc["journal"] = article.find("span", attrs={"class": "DocPublicationName"}).text.strip()
            except Exception as e:
                self._logger.warning("pas un article de presse")
                self._add_error(e, article)
                continue

            doc_header = article.find("span", attrs={"class": "DocHeader"})
            doc_header = doc_header.text.strip() if doc_header else ""

            doc_sub_section = article.find("span", attrs={"class": "DocTitreSousSection"})
            doc_sub_section = doc_sub_section.find_next_sibling("span").text.strip() if doc_sub_section else ""

            # date = find_date(doc_header or doc_sub_section)
            # if date:
            #     doc["date"] = date.strftime("%Y %m %d")
            #     doc["annee"] = date.year
            #     doc["mois"] = date.month
            #     doc["jour"] = date.day
            #     doc["epoch"] = date.toordinal()
            #
            # else:
            #     doc["date"] = None
            #     doc["annee"] = None
            #     doc["mois"] = None
            #     doc["jour"] = None
            #     doc["epoch"] = None

            datetime = find_datetime(doc_header or doc_sub_section)
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
                doc_titre_full = article.find("p", attrs={"class": "titreArticleVisu"})


            try:
                doc["titre"] = doc_titre_full.find("p", attrs={"class": "sm-margin-TopNews titreArticleVisu rdp__articletitle"}).text.strip()
            except AttributeError:
                try:
                    doc["titre"] = doc_titre_full.find("div", attrs={"class": "titreArticleVisu"}).text.strip()
                except AttributeError:
                    try:
                        doc["titre"] = doc_titre_full.text.strip()
                    except AttributeError:
                        raise

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
                corpus.append(Pivot(**doc))
                ids.add(id_)

        return corpus
