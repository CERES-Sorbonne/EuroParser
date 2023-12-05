from __future__ import annotations

import concurrent.futures
from typing import Tuple

from tqdm import tqdm

from europarser.models import Output, FileToTransform, OutputFormat, Pivot, TransformerOutput
from europarser.transformers.csv import CSVTransformer
from europarser.transformers.iramuteq import IramuteqTransformer
from europarser.transformers.json import JSONTransformer
from europarser.transformers.markdown import MarkdownTransformer
from europarser.pivot import PivotTransformer
from europarser.transformers.txm import TXMTransformer
from europarser.transformers.stats import StatsTransformer

transformer_factory = {
    "json": JSONTransformer().transform,
    "txm": TXMTransformer().transform,
    "iramuteq": IramuteqTransformer().transform,
    "gephi": None,
    "csv": CSVTransformer().transform,
    "stats": StatsTransformer().transform,
    "processed_stats": None,
    "plots": StatsTransformer().get_plots,
    "markdown": MarkdownTransformer().transform
}


def pipeline(files: list[FileToTransform], outputs: list[Output] = None) -> list[TransformerOutput]:
    """
    main function that transforms the files into pivots and then in differents required ouptputs
    """

    pivots: list[Pivot] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(PivotTransformer().transform, f) for f in files]
        for future in concurrent.futures.as_completed(futures):
            pivots = [*pivots, *future.result()]
        # undouble remaining doubles
        pivots = sorted(set(pivots), key=lambda x: x.epoch)

    to_process = []
    for output in outputs:
        if output != "processed_stats":
            func = transformer_factory[output]
            args = [pivots]
            to_process.append((func, args))
        # TODO: add processed_stats to the pipeline and reuse the stats transformer to avoid double processing

    results: list[TransformerOutput] = []

    with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(func, *args) for func, args in to_process]
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
            res = future.result()
            results.append(res)

    return results


def process(*args, **kwargs) -> list[TransformerOutput]:
    return pipeline(*args, **kwargs)