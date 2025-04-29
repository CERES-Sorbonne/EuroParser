from pathlib import Path
from typing import Optional

from filedetect import FileDetect

try:
    from . import pipeline
    from .models import FileToTransform, TransformerOutput, Params, Outputs, TXM_MODE
except ImportError:
    from europarser import pipeline
    from europarser.models import FileToTFileToTransform, TransformerOutput, Params, Outputs, TXM_MODE

def main(folder: Path | str, outputs: list[Outputs], params: Optional[Params] = None) -> None:
    if params is None:
        params = Params()

    if isinstance(folder, str):
        folder = Path(folder)
    elif not isinstance(folder, Path):
        raise ValueError(f"folder must be a Path or a string, not {type(folder)}")


    files = FileDetect.find(
        path=folder,
        suffixes={".html", ".json"},
    )
    if len(files) == 0:
        raise ValueError(f"No files found in {folder}")

    print(f"Found {len(files)} files")

    files = [
        FileToTransform(name=f.name, file=f.read_text(encoding="utf-8")) for f in files
    ]

    # process result
    results: list[TransformerOutput] = pipeline(files, outputs, params=params)

    # write results
    folder = folder / 'results'
    folder.mkdir(exist_ok=True)
    for result in results:
        print(result.filename)
        if isinstance(result.data, str):
            with open(folder / f'{result.filename}', 'w', encoding='utf-8') as f:
                f.write(result.data)
        else:
            with open(folder / f'{result.filename}', 'wb') as f:
                f.write(result.data)



if __name__ == '__main__':
    folder = Path('/mnt/P2/PycharmProjects/EuropressParser/test_emile')
    # outputs = ["json", "txm", "iramuteq", "csv", "excel", "stats", "processedStats", "markdown", "dynamicGraphs"]
    # outputs = ["json", "stats", "processed_stats", "plots"]
    outputs = ["txm"]
    params = Params(
        minimal_support_kw=5,
        minimal_support_authors=2,
        minimal_support_journals=8,
        minimal_support_dates=3,
        filter_keywords=True,
        filter_lang=True,
        txm_mode="multiple_files"
    )
    main(folder, outputs, params=params)
