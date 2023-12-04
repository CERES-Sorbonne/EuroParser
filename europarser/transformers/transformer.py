import sys

# if sys.version_info < (3, 9):
#     from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from abc import ABC
from typing import List
import re

import unicodedata

from europarser.models import Error, Pivot, OutputFormat, TransformerOutput


class Transformer(ABC):
    def __init__(self):
        self.name: str = type(self).__name__.split('Transformer')[0].lower()
        self.errors: List[Error] = []
        self._logger = logging.getLogger(self.name)
        self.output_type = "json"

    def transform(self, pivot: List[Pivot]) -> TransformerOutput:
        """
        Returns the transformed data, the output_type, and the output_filename
        """
        pass

    def _add_error(self, error, article):
        self.errors.append(Error(message=str(error), article=article.text, transformer=self.name))

    def _persist_errors(self, filename):
        """
        Save all errors to disk
        :param filename: name of the file being transformed
        """
        dir_path = Path(os.path.join(str(Path.home()), 'europarser'))
        dir_path.mkdir(parents=True, exist_ok=True)
        path = os.path.join(dir_path, f"errors-{filename}.json")
        mode = "a" if os.path.exists(path) else "w"
        with open(path, mode, encoding="utf-8") as f:
            json.dump([e.dict() for e in self.errors], f, ensure_ascii=False)

    @staticmethod
    def _format_value(value: str):
        # value = re.sub(r"[éèê]", "e", value)
        # value = re.sub(r"ô", "o", value)
        # value = re.sub(r"à", "a", value)
        # value = re.sub(r"œ", "oe", value)
        # value = re.sub(r"[ïîì]", "i", value)
        value = strip_accents(value)
        value = re.sub(r"""[-\[\]'":().=?!,;<>«»—^*\\/|]""", ' ', value)
        return ''.join([w.capitalize() for w in value.split(' ')])

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if unicodedata.category(c) != 'Mn')