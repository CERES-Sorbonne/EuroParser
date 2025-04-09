import json
from typing import List

from .models import Pivot, FileToTransform


def adjust_fields(elem: dict) -> dict:
    elem["keywords"] = set(e.strip() for e in elem.get("keywords", "").split(","))

    return elem


def do_one_file(file: FileToTransform) -> List[Pivot]:
    return [
        Pivot.parse_obj(
            adjust_fields(elem)
        )
        for elem in json.loads(file.file).values()
    ]


def pivots_from_files(
        files: List[FileToTransform],
) -> List[Pivot]:
    pivots = []

    for path in files:
        try:
            pivots.extend(do_one_file(path))
        except Exception as e:
            raise ValueError(f"Error parsing pivot file {path.name}: {e}")

    return pivots
