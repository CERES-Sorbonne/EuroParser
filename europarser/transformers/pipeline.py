import sys

# if sys.version_info < (3, 9):
#     from __future__ import annotations

import concurrent.futures
import json
from typing import List, Tuple, Any

from europarser.models import FileToTransform, Output, Pivot, OutputType
from europarser.transformers.gephi import GephiTransformer
from europarser.transformers.iramuteq import IramuteqTransformer
from europarser.transformers.csv_transformer import CSVTransformer
from europarser.transformers.pivot import PivotTransformer
from europarser.transformers.txm import TXMTransformer
from europarser.transformers.stats import StatsTransformer


def process(file: str, output: Output = "pivot", name: str = "file"):
    """
    utility function to process only one file at a time
    For multiple files, it's better to use the pipeline
    """
    return pipeline([FileToTransform(file=file, name=name)], output)


def pipeline(files: List[FileToTransform], outputs: List[Output] = ["pivot"]):  # -> Tuple[List[str, bytes], List[OutputType]]:
    pivots: List[Pivot] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(PivotTransformer().transform, f) for f in files]
        for future in concurrent.futures.as_completed(futures):
            pivots = [*pivots, *future.result()]
        # undouble remaining doubles
        pivots = sorted(set(pivots), key=lambda x: x.epoch)

    if "stats" in outputs or "processed_stats" in outputs or "plots" in outputs:
        stats_data = StatsTransformer().transform(pivots)
    else:
        stats_data = None
    results: List[dict[str, OutputType | Any] | bytes] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_output, output, pivots, stats_data) for output in outputs]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            results.append({'type': res[1], 'data': res[0], 'output': res[2]})
    if not results:
        results.append({'data': json.dumps([pivot.dict() for pivot in pivots], ensure_ascii=False), 'output': 'json'})
    return results


def process_output(output: Output, pivots: List[Pivot], stats_data: dict) -> Tuple:
    stats_transformer = None
    if stats_data is not None and output in ["processed_stats", "plots"]:
        stats_transformer = StatsTransformer()
        stats_transformer.data = stats_data

    match output:
        case "json":
            return json.dumps({i: article.dict() for i, article in enumerate(pivots)}, ensure_ascii=False), "json", output
        case "iramuteq":
            return IramuteqTransformer().transform(pivots), "txt", output
        case "txm":
            return TXMTransformer().transform(pivots), "xml", output
        case "csv":
            return CSVTransformer().transform(pivots), "csv", output
        case "stats":
            return json.dumps(stats_data, ensure_ascii=False, indent=2), "json", output
        case "processed_stats":
            return stats_transformer.get_stats(pivots), "zip", output
        case "plots":
            return stats_transformer.get_plots(pivots), "zip", output
