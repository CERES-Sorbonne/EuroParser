import hashlib
import sys

# if sys.version_info < (3, 9):
#     from __future__ import annotations

import concurrent.futures
import json
from pathlib import Path
from typing import List, Tuple, Any

from europarser.models import FileToTransform, Output, Pivot, OutputFormat
from europarser.transformers.gephi import GephiTransformer
from europarser.transformers.iramuteq import IramuteqTransformer
from europarser.transformers.csv import CSVTransformer
from europarser.transformers.pivot import PivotTransformer
from europarser.transformers.txm import TXMTransformer
from europarser.transformers.stats import StatsTransformer

global savedir
savedir = Path(__file__)
while savedir.name != "EuropressParser":
    # print(savedir.name)
    savedir = savedir.parent
    if not savedir:
        raise FileNotFoundError("Could not find `EuropressParser` directory which should be the root of the project")

savedir = savedir / "parsed_data"
savedir.mkdir(exist_ok=True)

def process(file: str, output: Output = "pivot", name: str = "file"):
    """
    utility function to process only one file at a time
    For multiple files, it's better to use the pipeline
    """
    return pipeline([FileToTransform(file=file, name=name)], output)


def pipeline(files: List[FileToTransform], outputs=None):  # -> Tuple[List[str, bytes], List[OutputType]]:
    if outputs is None:
        outputs = ["pivot"]
    pivots: List[Pivot] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(PivotTransformer().transform, f) for f in files]
        for future in concurrent.futures.as_completed(futures):
            pivots = [*pivots, *future.result()]
        # undouble remaining doubles
        pivots = sorted(set(pivots), key=lambda x: x.epoch)

    json_ver = json.dumps({i: article.dict() for i, article in enumerate(pivots)}, ensure_ascii=False)
    hash_json = hashlib.sha256(json_ver.encode()).hexdigest()
    with (savedir / f"{hash_json}.json").open("w", encoding="utf-8") as f:
        f.write(json_ver)

    if "stats" in outputs or "processed_stats" in outputs or "plots" in outputs:
        st = StatsTransformer()
        st.transform(pivots)
        stats_data = {
            key: value
            for key, value in st.__dict__.items()
            if not key.startswith("_")
        }
    else:
        stats_data = {}

    results: List[dict[str, OutputFormat | Any] | bytes] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_output, output, pivots, stats_data.copy(), json_ver) for output in outputs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            results.append({'type': res[1], 'data': res[0], 'output': res[2]})
    if not results:
        results.append({'data': json.dumps([pivot.dict() for pivot in pivots], ensure_ascii=False), 'output': 'json'})
    return results


def process_output(
        output: Output,
        pivots: List[Pivot],
        stats_data: dict,
        json_data: dict = None,
) -> Tuple:
    stats_transformer = None
    if (stats_data is not None or stats_data == {}) and output in ["processed_stats", "plots"]:
        stats_transformer = StatsTransformer()
        for key, value in stats_data.items():
            setattr(stats_transformer, key, value)

    match output:
        case "json":
            return json_data, "json", output
        case "iramuteq":
            return IramuteqTransformer().transform(pivots), "txt", output
        case "txm":
            return TXMTransformer().transform(pivots), "xml", output
        case "csv":
            return CSVTransformer().transform(pivots), "csv", output
        case "stats":
            return json.dumps(stats_data['res'], ensure_ascii=False, indent=2), "json", output
        case "processed_stats":
            return stats_transformer.get_stats(pivots), "zip", output
        case "plots":
            return stats_transformer.get_plots(pivots), "zip", output
