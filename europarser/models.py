import sys

# if sys.version_info < (3, 9):
#     from __future__ import annotations

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
    journal_clean: str
    titre: str
    sous_titre: str
    annee: int
    mois: int
    jour: int
    date: str
    epoch: int
    auteur: str
    texte: str
    keywords: str
    langue: str

    def __hash__(self):
        return hash((self.journal, self.date, self.titre))


OutputType = Literal["csv", "json", "txt", "xml", "zip"]
Output = Literal["json", "txm", "iramuteq", "gephi", "cluster_tool", "csv", "stats", "processed_stats", "plots"]
