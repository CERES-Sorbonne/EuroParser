from typing import Literal

from pydantic import BaseModel


class FileToTransform(BaseModel):
    name: str
    file: str


class Error(BaseModel):
    message: str
    article: str
    transformer: str


class Pivot(BaseModel):
    journal: str
    journal_clean : str
    titre: str
    date: str
    auteur: str
    texte: str
    keywords: str
    langue :str

    def __hash__(self):
        return hash((self.journal, self.date, self.titre))


OutputType = Literal["csv", "json", "txt", "xml"]
Output = Literal["json", "txm", "iramuteq", "gephi", "cluster_tool", "csv"]
