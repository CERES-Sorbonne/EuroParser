from pathlib import Path

from europarser import process
from europarser.models import FileToTransform, TransformerOutput, Params, Output


def main(file: Path, outputs: list[Output]) -> None:
    with open(file, 'r', encoding='utf-8') as f:
        file = FileToTransform(name=file.name, file=f.read())

    results: list[TransformerOutput] = process(file, outputs, Params())

    folder = file.parent / 'results'
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
    file = Path(__file__).parent / 'resources' / '1.HTML'
    outputs = ["json", "stats", "processed_stats", "plots"]
    main(file, outputs)
