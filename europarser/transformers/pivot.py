from typing import List
from bs4 import BeautifulSoup

from europarser.models import FileToTransform, Pivot
from europarser.transformers.transformer import Transformer
from europarser.utils import dic_months, find_date


class PivotTransformer(Transformer):
    def __init__(self):
        super().__init__()

    def transform(self, file_to_transform: FileToTransform) -> List[Pivot]:
        self._logger.warning("Processing file " + file_to_transform.name)
        soup = BeautifulSoup(file_to_transform.file, 'html.parser')

        corpus = []

        articles = soup.find_all("article")
        for article in articles:
            doc = {}
            try:
                doc["journal"] = article.find("span", attrs={"class": "DocPublicationName"}).text.strip()
            except Exception as e:
                self._logger.warning("pas un article de presse")
                self._add_error(e, article)
                continue
            try:
                doc_header = article.find("span", attrs={"class": "DocHeader"})
                year = day_nb = month = None
                # is there a doc header ?
                if doc_header:
                    text = doc_header.text.strip()
                    day_nb, month, year = find_date(text)

                # if no date was found yet look in another section
                if not month:
                    doc_sub_section = article.find("span", attrs={"class": "DocTitreSousSection"}).find_next_sibling("span").text.strip()
                    day_nb, month, year = doc_sub_section.split()[:3]

                if not all([year, month, day_nb]):
                    print("No proper date was found")
                    continue
            except Exception as e:
                print("New unhandled case " + str(e))
                continue

            doc["date"] = " ".join([year, dic_months[month], day_nb])

            try:
                doc["titre"] = article.find("div", attrs={"class": "titreArticle"}).text.strip()
            except:
                doc["titre"] = article.find("p", attrs={"class": "titreArticleVisu"}).text.strip()
            try:
                doc["texte"] = article.find("div", attrs={"class": "docOcurrContainer"}).text.strip()
            except:
                doc["texte"] = article.find("div", attrs={"class": "DocText clearfix"}).text.strip()

            corpus.append(Pivot(**doc))



        return corpus

