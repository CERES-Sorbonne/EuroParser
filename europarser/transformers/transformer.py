import sys

# if sys.version_info < (3, 9):
#     from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from abc import ABC
from typing import List

from europarser.models import Error, Pivot


class Transformer(ABC):
    def __init__(self):
        self.type: str = type(self).__name__
        self.errors: List[Error] = []
        self._logger = logging.getLogger(self.type)

    def transform(self, pivot: List[Pivot]) -> str:
        pass

    def _add_error(self, error, article):
        self.errors.append(Error(message=str(error), article=article.text, transformer=self.type))

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
