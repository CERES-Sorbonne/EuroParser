from typing import List, Dict, Any
from bs4 import BeautifulSoup

from europarser.models import FileToTransform, Pivot
from europarser.transformers.transformer import Transformer
from europarser.utils import find_date
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

            day_nb, month, year = find_date(doc_header or doc_sub_section)

            if not all([year, month, day_nb]):
                print("No proper date was found")
                continue

            doc["date"] = " ".join([year, month, day_nb])

            try:
                doc["titre"] = article.find("div", attrs={"class": "titreArticle"}).text.strip()
            except:
                doc["titre"] = article.find("p", attrs={"class": "titreArticleVisu"}).text.strip()
            try:
                doc["texte"] = article.find("div", attrs={"class": "docOcurrContainer"}).text.strip()
            except:
                if article.find("div", attrs={"class": "DocText clearfix"}) is None:
                    continue
                else:
                    doc["texte"] = article.find("div", attrs={"class": "DocText clearfix"}).text.strip()

            try:
                doc["auteur"] = article.find("div", attrs={"class": "docAuthors"}).text.strip().lower()
            except:
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
