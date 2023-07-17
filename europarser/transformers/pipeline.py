import concurrent.futures
import json
from typing import List, Tuple

from europarser.models import FileToTransform, Output, Pivot, OutputType
from europarser.transformers.iramuteq import IramuteqTransformer
from europarser.transformers.csv import CSVTransformer
from europarser.transformers.pivot import PivotTransformer
from europarser.transformers.txm import TXMTransformer
from europarser.transformers.stats import StatsTransformer


def process(file: str, output: Output = "pivot", name: str = "file"):
    """
    utility function to process only one file at a time
    For multiple files, it's better to use the pipeline
    """
    return pipeline([FileToTransform(file=file, name=name)], output)


def pipeline(files: List[FileToTransform], output: Output = "pivot") -> Tuple[List[str | bytes], List[OutputType]]:
    pivots: List[Pivot] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(PivotTransformer().transform, f) for f in files]
        for future in concurrent.futures.as_completed(futures):
            pivots = [*pivots, *future.result()]
        # undouble remaining doubles
        pivots = list(set(pivots))

    results: List[str | bytes] = []
    results_types: List[OutputType] = []
    if "json" in output:
        results.append(json.dumps({i: article.dict() for i, article in enumerate(pivots)}, ensure_ascii=False))
        results_types.append("json")
    if "iramuteq" in output:
        results.append(IramuteqTransformer().transform(pivots))
        results_types.append("txt")
    if "txm" in output:
        results.append(TXMTransformer().transform(pivots))
        results_types.append("xml")
    if "csv" in output:
        results.append(CSVTransformer().transform(pivots))
        results_types.append("csv")
    if "stats" in output:
        results.append(json.dumps(StatsTransformer().transform(pivots), ensure_ascii=False, indent=2))
        results_types.append("json")
    if "processed_stats" in output:
        results.append(StatsTransformer().get_stats(pivots))
        results_types.append("zip")
    if not results:
        results.append(json.dumps([pivot.dict() for pivot in pivots], ensure_ascii=False))
        results_types.append("json")
    return results, results_types
