import concurrent.futures
import hashlib
import json
from builtins import function
from multiprocessing import Lock, Pool
from pathlib import Path
from typing import List, Tuple, Any, Set

from tqdm.auto import tqdm

from europarser.models import FileToTransform, Output, Pivot, OutputType
from europarser.transformers.csv_transformer import CSVTransformer
from europarser.transformers.iramuteq import IramuteqTransformer
from europarser.transformers.pivot import PivotTransformer
from europarser.transformers.stats import StatsTransformer
from europarser.transformers.txm import TXMTransformer

global savedir
savedir = Path(__file__)
while savedir.name != "EurpressParser":
    savedir = savedir.parent

savedir = savedir / "parsed_data"
savedir.mkdir(exist_ok=True)


def make_json(pivots: List[Pivot], num: int = 0) -> Tuple[str, int]:
    json_ver = json.dumps({i: article.dict() for i, article in enumerate(pivots)}, ensure_ascii=False)
    hash_json = hashlib.sha256(json_ver.encode()).hexdigest()
    with (savedir / f"{hash_json}.json").open("w", encoding="utf-8") as f:
        f.write(json_ver)
    return json_ver, num


def make_iramuteq(pivots: List[Pivot], num: int) -> Tuple[str, int]:
    return IramuteqTransformer.transform(pivots), num


def make_txm(pivots: List[Pivot], num: int) -> Tuple[str, int]:
    return TXMTransformer.transform(pivots), num


def make_csv(pivots: List[Pivot], num: int) -> Tuple[str, int]:
    return CSVTransformer.transform(pivots), num


def make_gephi(pivots: List[Pivot], num: int) -> Tuple[str, int]:
    raise NotImplementedError


def make_stats(pivots: List[Pivot], num: int, st: StatsTransformer, lock: Lock) -> Tuple[str, int]:
    Lock.acquire()
    res = st.transform(pivots)['res']
    Lock.release()
    return json.dumps(res, ensure_ascii=False, indent=2), num


def make_processed_stats(pivots: List[Pivot], num: int, st: StatsTransformer, lock: Lock) -> Tuple[str, int]:
    Lock.acquire()
    res = st.get_stats()
    Lock.release()
    return json.dumps(res, ensure_ascii=False, indent=2), num


def make_plots(pivots: List[Pivot], num: int, st: StatsTransformer, lock: Lock) -> Tuple[bytes, int]:
    return st.get_plots(), num


def pipeline_split(
        files: List[FileToTransform],
        outputs: List[Output] = None
) -> Tuple[List[str, bytes], List[OutputType], List[Output]]:


    outp_to_func: dict[Output, function] = {
        "json": make_json,
        "iramuteq": make_iramuteq,
        "txm": make_txm,
        "csv": make_csv,
        "gephi": make_gephi,
    }

    stats_outp: Set[str] = {"stats", "processed_stats", "plots"}

    outp_to_type: dict[Output, OutputType] = {
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

    num: int = 0

    if outputs is None:
        outputs = ["pivot"]

    pivots: List[Pivot] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(PivotTransformer().transform, f) for f in files]
        for future in concurrent.futures.as_completed(futures):
            pivots = [*pivots, *future.result()]
        # undouble remaining doubles
        pivots = sorted(set(pivots), key=lambda x: x.epoch)

    json_ver, _ = make_json(pivots)

    # Functions ang their arguments to process
    to_process: List[Tuple[function, Tuple[Any]]] = []
    for num, output in enumerate(outputs):
        if output in stats_outp:
            do_stats = True
            continue

        if output not in outp_to_func:
            raise ValueError(f"Output {output} not supported.")

        to_process.append((outp_to_func[output], (pivots, num)))

    if do_stats:
        st = StatsTransformer()
        lock = Lock()
        # to_process.append((make_stats, (pivots, num, st, lock)))

        for num, output in enumerate(outputs):
            if output not in stats_outp:
                continue

            elif output == "processed_stats":
                to_process.append((make_processed_stats, (pivots, num, st, lock)))
            elif output == "plots":
                to_process.append((make_plots, (pivots, num, st, lock)))

    else:
        st = None
        lock = None

    results: List[str | bytes, int] = []
    with Pool() as pool:
        pbar = tqdm(total=len(to_process))
        if do_stats:
            pool.apply_async(make_stats, (pivots, num, st, lock), callback=lambda x: results.append(x))
            pbar.update(1)
        for func, args in to_process:
            pool.apply_async(func, args, callback=lambda x: results.append(x))
            pbar.update(1)

        pool.close()
        pool.join()

    results = [x[0] for x in sorted(results, key=lambda x: x[1])]

    if not results:
        return [json_ver], ["json"], [Output.pivot]

    return results, [outp_to_type[output] for output in outputs], outputs





