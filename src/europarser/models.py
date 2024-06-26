from typing import Literal, Set, Union, Optional

from pydantic import BaseModel, field_serializer


class FileToTransform(BaseModel):
    name: str
    file: str


class Error(BaseModel):
    message: str
    article: str
    transformer: str


class Pivot(BaseModel):
    id: str
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
    keywords: Set[str]
    langue: str
    url: str

    def __hash__(self):
        return hash((self.journal, self.date, self.titre))

    @field_serializer('keywords')
    def serialize_keywords(self, kw: Set[str]):
        return ', '.join(kw)


OutputFormat = Literal["csv", "excel", "json", "txt", "xml", "zip"]
Output = Literal["json", "txm", "iramuteq", "gephi", "csv", "excel", "stats", "processed_stats", "plots", "markdown"]


class TransformerOutput(BaseModel):
    data: Union[str, bytes, None]
    output: OutputFormat
    filename: str


class Params:
    def __init__(
            self,
            filter_keywords: bool = False,
            filter_lang: bool = False,
            minimal_support: int = 1,
            minimal_support_kw: Optional[int] = None,
            minimal_support_journals: Optional[int] = None,
            minimal_support_authors: Optional[int] = None,
            minimal_support_dates: Optional[int] = None,
    ):
        assert all((isinstance(x, int) and x > 0) or x is None
                   for x in [minimal_support, minimal_support_kw, minimal_support_journals, minimal_support_authors,
                             minimal_support_dates])
        assert all(isinstance(x, bool) for x in [filter_keywords, filter_lang])

        self.filter_keywords: bool = filter_keywords
        self.filter_lang: bool = filter_lang
        self.minimal_support: int = minimal_support
        self.minimal_support_kw: int = minimal_support_kw or minimal_support
        self.minimal_support_journals: int = minimal_support_journals or minimal_support
        self.minimal_support_authors: int = minimal_support_authors or minimal_support
        self.minimal_support_dates: int = minimal_support_dates or minimal_support
