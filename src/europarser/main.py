from pathlib import Path
from typing import Optional

from . import pipeline
from .models import FileToTransform, TransformerOutput, Params, Outputs


def main(folder: Path | str, outputs: list[Outputs], params: Optional[Params] = None) -> None:
    if params is None:
        params = Params()

    if isinstance(folder, str):
        folder = Path(folder)
    elif not isinstance(folder, Path):
        raise ValueError(f"folder must be a Path or a string, not {type(folder)}")

    # parse all files
    files = []
    for file in folder.iterdir():
        if file.suffix.lower() != ".html":
            print(f"Skipping {file.name} (not an HTML file)")
            continue
        if file.is_file():
            with open(file, 'r', encoding='utf-8') as f:
                files.append(FileToTransform(name=file.name, file=f.read()))
    print(f"Processing {len(files)} files...")

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
    folder = Path('/home/marceau/Nextcloud/eurocollectes/15-18')
    outputs = ["json", "txm", "iramuteq", "csv", "excel", "stats", "processed_stats", "plots", "markdown"]
    outputs = ["json", "txm", "iramuteq", "csv", "excel", "stats", "processedStats", "markdown", "dynamicGraphs"]
    # outputs = ["json", "stats", "processed_stats", "plots"]
    params = Params(
        minimal_support_kw=5,
        minimal_support_authors=2,
        minimal_support_journals=8,
        minimal_support_dates=3,
    )
    main(folder, outputs, params=params)
