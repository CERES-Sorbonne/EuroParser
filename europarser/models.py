from __future__ import annotations

import io
import sys

# if sys.version_info < (3, 9):
#     from __future__ import annotations

from typing import Literal, Any

from pydantic import BaseModel, field_serializer


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
    complement: str
    annee: int
    mois: int
    jour: int
    heure: int
    minute: int
    seconde: int
    date: str
    epoch: int
    auteur: str
    texte: str
    keywords: list
    langue: str

    def __hash__(self):
        return hash((self.journal, self.date, self.titre))

    @field_serializer('keywords')
    def serialize_keywords(self, kw: list):
        return ', '.join(kw).strip()

OutputFormat = Literal["csv", "json", "txt", "xml", "zip"]
Output = Literal["json", "txm", "iramuteq", "gephi", "csv", "stats", "processed_stats", "plots", "markdown"]


class TransformerOutput(BaseModel):
    data: str | bytes | None
    output: OutputFormat
    filename: str


class Params:
    def __init__(self, filter_keywords: bool = False, filter_lang: bool = False):
        self.filter_keywords: bool = filter_keywords
        self.filter_lang: bool = filter_lang