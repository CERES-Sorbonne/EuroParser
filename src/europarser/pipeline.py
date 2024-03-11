from __future__ import annotations

import concurrent.futures

from tqdm.auto import tqdm

from .models import Output, FileToTransform, TransformerOutput, Params
from .transformers.to_csv import CSVTransformer
from .transformers.to_iramuteq import IramuteqTransformer
from .transformers.to_json import JSONTransformer
from .transformers.to_markdown import MarkdownTransformer
from .pivot import PivotTransformer
from .transformers.to_txm import TXMTransformer
from .transformers.to_stats import StatsTransformer

transformer_factory = {
    "json": JSONTransformer().transform,
    "txm": TXMTransformer().transform,
    "iramuteq": IramuteqTransformer().transform,
    "gephi": None,
    "csv": CSVTransformer().transform,
    "stats": "get_stats",
    "processed_stats": "get_processed_stats",
    "plots": "get_plots",
    "markdown": MarkdownTransformer().transform
}

stats_outputs = {"stats", "processed_stats", "plots", "markdown"}


def pipeline(files: list[FileToTransform], outputs: list[Output], params: Params) -> list[TransformerOutput]:
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

        # if not isinstance(outputs, (Output, str, OutputFormat)):
        #     raise ValueError(f"Unknown output type: {output}")

    if not isinstance(params, Params):
        raise ValueError(f"Unknown params type: {params}")

    transformer = PivotTransformer(params)
    pivots = transformer.transform(files_to_transform=files)

    to_process = []
    st = None
    if stats_outputs.intersection(outputs):
        st = StatsTransformer()
        st.transform(pivots)

    for output in outputs:
        if output in stats_outputs and output != "markdown":
            func = getattr(st, transformer_factory[output])
            to_process.append((func, []))

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
