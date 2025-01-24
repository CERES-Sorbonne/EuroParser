import json
import logging
from os import getenv
from pathlib import Path
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Union
import re

import unicodedata
from bs4 import BeautifulSoup, Tag

from ..models import Error, Pivot, TransformerOutput, Params

# Transformer initialization, allows all transformers to access the output path end prevents to set it multiple times

output_path = getenv("EUROPARSER_OUTPUT", None)

if output_path is None:
    logging.warning("EUROPARSER_OUTPUT not set, disabling output")
else:
    output_path = Path(output_path)

    if not output_path.is_dir():
        logging.warning(f"Output path {output_path} is not a directory, disabling output")
        output_path = None

if output_path:
    output_path.mkdir(parents=True, exist_ok=True)

caracteres_speciaux = re.compile(r"[^\w\s]", re.UNICODE)
espaces_et_slashs = re.compile(r'(\s+)|([/\\]+)', re.UNICODE)

class Transformer(ABC):
    output_path = output_path

    def __init__(self, params: Optional[Params] = None, **kwargs: Optional[Any]):
        self.name: str = type(self).__name__.split('Transformer')[0].lower()
        self.errors: List[Error] = []
        self._logger = logging.getLogger(self.name)
        self._logger.setLevel(logging.WARNING)
        # self.output_type = "json" # TODO any use of setting the output type ? Should maybe be a None ?
        self.params = params or Params(
            **kwargs)  # If no kwargs are passed, params will be initialized with default values

    @abstractmethod
    def transform(self, pivot: List[Pivot]) -> TransformerOutput:
        """
        Returns the transformed data, the output_type, and the output_filename
        """
        raise NotImplementedError()

    def _add_error(self, error: Exception, article: Union[Pivot, BeautifulSoup, Tag]) -> None:
        self.errors.append(Error(message=str(error), article=article.text, transformer=self.name))

    def _persist_errors(self, filename: str) -> None:
        """
        Save all errors to disk
        :param filename: name of the file being transformed
        """
        dir_path = Path.home() / "europarser"
        dir_path.mkdir(parents=True, exist_ok=True)
        path = dir_path / f"errors-{filename}.json"
        mode = "a" if path.exists() else "w"
        with path.open(mode, encoding="utf-8") as f:
            json.dump([e.dict() for e in self.errors], f, ensure_ascii=False)
        print(f"Errors saved to {path}")

    @staticmethod
    def _format_value(value: str) -> str:
        # value = re.sub(r"[éèê]", "e", value)
        # value = re.sub(r"ô", "o", value)
        # value = re.sub(r"à", "a", value)
        # value = re.sub(r"œ", "oe", value)
        # value = re.sub(r"[ïîì]", "i", value)
        value = strip_accents(value)
        value = re.sub(r"""[-\[\]'":().=?!,;<>«»—^*\\/|]""", ' ', value)
        return ''.join([w.capitalize() for w in value.split(' ')])

    @staticmethod
    def _to_pascal(string: str) -> str:
        return "".join(x.capitalize() for x in string.lower().split("_"))

    @staticmethod
    def _to_camel(string: str) -> str:
        return "".join(
            x.capitalize()
            if i > 0
            else x.lower()
            for i, x in enumerate(string.lower().split("_"))
        )

    @staticmethod
    def clean_string(s):
        """
        Fonction pour nettoyer les chaînes de caractères pour les noms de fichiers (et le frontmatter YAML)
        """
        s = caracteres_speciaux.sub("", s)
        s = s.lower()
        s = s.strip()
        s = espaces_et_slashs.sub('_', s)
        return s


def strip_accents(string: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', string) if unicodedata.category(c) != 'Mn')
