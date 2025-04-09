from __future__ import annotations

import concurrent.futures

from tqdm.auto import tqdm

from .models import Outputs, FileToTransform, TransformerOutput, Params
from .pivot import PivotTransformer
from .transformers.to_csv import CSVTransformer
from .transformers.to_excel import ExcelTransformer
from .transformers.to_iramuteq import IramuteqTransformer
from .transformers.to_json import JSONTransformer
from .transformers.to_markdown import MarkdownTransformer
from .transformers.to_stats import StatsTransformer
from .transformers.to_txm import TXMTransformer
from .pivots_from_files import pivots_from_files

transformer_factory = {
    "json": JSONTransformer().transform,
    "txm": TXMTransformer().transform,
    "iramuteq": IramuteqTransformer().transform,
    "gephi": None,
    "csv": CSVTransformer().transform,
    "excel": ExcelTransformer().transform,
    "stats": "get_stats",
    "processedStats": "get_processed_stats",
    "dynamicGraphs": "get_plots",
    "markdown": MarkdownTransformer().transform
}

stats_outputs = {"stats", "processedStats", "dynamicGraphs", "markdown"}
not_implemented = {"staticGraphs"}


def pipeline(files: list[FileToTransform], outputs: list[Outputs], params: Params) -> list[TransformerOutput]:
    """
    main function that transforms the files into pivots and then in differents required ouptputs
    """

    if not isinstance(files, list):
        files = [files]

    for file in files:
        if not isinstance(file, FileToTransform):
            raise ValueError(f"Unknown file type: {file}")

    if not isinstance(outputs, list):
        outputs = [outputs]

    for output in outputs:
        if output not in transformer_factory:
            raise ValueError(f"Unknown output type: {output}")

    if not isinstance(params, Params):
        raise ValueError(f"Unknown params type: {params}")

    # Séparer les fichiers HTML et JSON en se basant sur le suffixe
    html_files = [f for f in files if f.name.lower().endswith('.html')]
    json_files = [f for f in files if f.name.lower().endswith('.json')]

    pivots = []
    if html_files:
        transformer = PivotTransformer(params)
        pivots.extend(transformer.transform(files_to_transform=html_files))
    if json_files:
        pivots.extend(pivots_from_files(json_files))

    pivots = sorted(pivots, key=lambda x: x.epoch)

    to_process = []
    st = None
    if stats_outputs.intersection(outputs):
        st = StatsTransformer(params)
        st.transform(pivots)

    for output in outputs:
        if output in not_implemented:
            raise NotImplementedError(f"{output} is not implemented yet")

        if output in stats_outputs and output != "markdown":
            func = getattr(st, transformer_factory[output])
            to_process.append((func, []))
            
        elif output == "txm":
            func = transformer_factory[output]
            args = [pivots, params.txm_mode]
            to_process.append((func, args))

        else:
            func = transformer_factory[output]
            args = [pivots]
            to_process.append((func, args))

    results: list[TransformerOutput] = []

    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = [executor.submit(func, *args) for func, args in to_process]
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
            res = future.result()
            results.append(res)

    return results

