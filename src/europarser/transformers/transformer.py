import json
import logging
import os
from pathlib import Path
from abc import ABC, abstractmethod
from typing import List, Optional, Any
import re

import unicodedata

from ..models import Error, Pivot, TransformerOutput, Params

# Transformer initialization, allows all transformers to access the output path end prevents to set it multiple times

output_path = os.getenv("EUROPARSER_OUTPUT", None)

if output_path is None:
    logging.warning("EUROPARSER_OUTPUT not set, disabling output")
else:
    output_path = Path(output_path)

    if not output_path.is_dir():
        logging.warning(f"Output path {output_path} is not a directory, disabling output")
        output_path = None

if output_path:
    output_path.mkdir(parents=True, exist_ok=True)


class Transformer(ABC):
    output_path = output_path

    def __init__(self, params: Optional[Params] = None, **kwargs: Optional[Any]):
        self.name: str = type(self).__name__.split('Transformer')[0].lower()
        self.errors: List[Error] = []
        self._logger = logging.getLogger(self.name)
        self._logger.setLevel(logging.WARNING)
        # self.output_type = "json" # TODO any use of setting the output type ? Should maybe be a None ?
        self.params = params or Params(**kwargs)  # If no kwargs are passed, params will be initialized with default values

    @abstractmethod
    def transform(self, pivot: List[Pivot]) -> TransformerOutput:
        """
        Returns the transformed data, the output_type, and the output_filename
        """
        raise NotImplementedError()

    def _add_error(self, error: Exception, article: Pivot) -> None:
        self.errors.append(Error(message=str(error), article=article.text, transformer=self.name))

    def _persist_errors(self, filename: str) -> None:
        """
        Save all errors to disk
        :param filename: name of the file being transformed
        """
        dir_path = Path.home() / "europarser"
        dir_path.mkdir(parents=True, exist_ok=True)
        path = os.path.join(dir_path, f"errors-{filename}.json")
        mode = "a" if os.path.exists(path) else "w"
        with open(path, mode, encoding="utf-8") as f:
            json.dump([e.dict() for e in self.errors], f, ensure_ascii=False)

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

def strip_accents(string: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', string) if unicodedata.category(c) != 'Mn')
