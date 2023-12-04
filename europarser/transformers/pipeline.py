from __future__ import annotations

import concurrent.futures
import hashlib
import json
from multiprocessing import Lock, Pool
from pathlib import Path
from typing import List, Tuple, Any, Set

from tqdm.auto import tqdm

from europarser.models import FileToTransform, Output, Pivot, OutputFormat
from europarser.transformers.csv import CSVTransformer
from europarser.transformers.iramuteq import IramuteqTransformer
from europarser.pivot import PivotTransformer
from europarser.transformers.stats import StatsTransformer
from europarser.transformers.txm import TXMTransformer




def make_json(pivots: List[Pivot], num: int = 0) -> Tuple[str, int]:
    json_ver = json.dumps({i: article.dict() for i, article in enumerate(pivots)}, ensure_ascii=False)
    hash_json = hashlib.sha256(json_ver.encode()).hexdigest()
    with (savedir / f"{hash_json}.json").open("w", encoding="utf-8") as f:
        f.write(json_ver)
    return json_ver, num


def make_iramuteq(pivots: List[Pivot], num: int) -> Tuple[str, int]:
    return IramuteqTransformer().transform(pivots), num


def make_txm(pivots: List[Pivot], num: int) -> Tuple[str, int]:
    return TXMTransformer().transform(pivots), num


def make_csv(pivots: List[Pivot], num: int) -> Tuple[str, int]:
    return CSVTransformer().transform(pivots), num


def make_gephi(pivots: List[Pivot], num: int) -> Tuple[str, int]:
    raise NotImplementedError


def make_stats(num: int, st: StatsTransformer) -> Tuple[str, int]:
    return json.dumps(st.res, ensure_ascii=False, indent=2), num


def make_processed_stats(num: int, st: StatsTransformer) -> Tuple[str, int]:
    return json.dumps(st.get_stats(), ensure_ascii=False, indent=2), num


def make_plots(num: int, st: StatsTransformer) -> Tuple[bytes, int]:
    return st.get_plots(), num


def pipeline(files: List[FileToTransform], outputs: List[Output] = None) -> Tuple[dict[str, OutputFormat | str | bytes], ...]:
    """
    main function that transforms the files into pivots and then in differents required ouptputs
    """
    outp_to_func: dict[Output, Any] = {
        "json": make_json,
        "iramuteq": make_iramuteq,
        "txm": make_txm,
        "csv": make_csv,
        "gephi": make_gephi
    }
    stats_outp: Set[str] = {"stats", "processed_stats", "plots"}
    outp_to_type: dict[Output, OutputFormat] = {
        "json": "json",
        "iramuteq": "txt",
        "txm": "xml",
        "csv": "csv",
        "gephi": "csv",
        "stats": "json",
        "processed_stats": "json",
        "plots": "zip",
    }
    do_stats: bool = False

    st: StatsTransformer
    num: int
    futures: List[concurrent.futures.Future]
    res: Tuple[str, int]
    result: Tuple[dict[str, OutputFormat | str | bytes], ...]

    # Functions ang their arguments to process
    to_process: List[Tuple[Any, Tuple[Any]]] = []

    if outputs is None:
        outputs = ["pivot"]

    pivots: List[Pivot] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(PivotTransformer().transform, f) for f in files]
        for future in concurrent.futures.as_completed(futures):
            pivots = [*pivots, *future.result()]
        # undouble remaining doubles
        pivots = sorted(set(pivots), key=lambda x: x.epoch)

    for num, output in enumerate(outputs):
        if output in stats_outp:
            do_stats = True
            continue
        if output not in outp_to_func:
            raise ValueError(f"Output {output} not supported.")

        to_process.append((outp_to_func[output], (pivots, num)))

    if do_stats:
        st = StatsTransformer()
        st.transform(pivots)
        for num, output in enumerate(outputs):
            if output not in stats_outp:
                continue

            if output == "stats":
                to_process.append((make_stats, (num, st)))
            elif output == "processed_stats":
                to_process.append((make_processed_stats, (num, st)))
            elif output == "plots":
                to_process.append((make_plots, (num, st)))

    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(func, *args) for func, args in to_process]
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
            res = future.result()
            results.append(res)

    results = sorted(results, key=lambda x: x[1])

    if any(r[1] == -1 for r in results):
        raise ValueError

    results = [result[0] for result in results]

    if not results:
        return ({"data": make_json(pivots)[0], "type": "json", "output": "json"},)

    result = tuple(
        {
            "data": res,
            "type": outp_to_type[output],
            "output": output
        }
        for res, output in zip(results, outputs)
    )

    # Ensures that the json output is computed, even if it's not in the outputs
    try:
        return result
    finally:
        if not any(output == "json" for output in outputs):
            json_ver, _ = make_json(pivots)


def process(file: str, output: Output = "pivot", name: str = "file"):
    """
    utility function to process only one file at a time
    For multiple files, it's better to use the pipeline
    """
    return pipeline([FileToTransform(file=file, name=name)], output)
