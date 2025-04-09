from enum import Enum
from pathlib import Path
from typing import Generator, Optional, Set, Iterable, Union

video_formats = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpeg", ".mpg", ".3gp", ".3g2"}
image_formats = {".jpg"}
audio_formats = {".wav", ".aac", ".mp3"}
text_formats = {".txt"}
csv_formats = {".csv"}
json_formats = {".json"}
html_formats = {".html"}

map_formats = {
    "video": video_formats,
    "image": image_formats,
    "audio": audio_formats,
    "text": text_formats,
    "csv": csv_formats,
    "json": json_formats,
    "html": html_formats
}


class FileType(Enum):
    video = video_formats
    image = image_formats
    audio = audio_formats
    text = text_formats
    csv = csv_formats
    json = json_formats
    html = html_formats


def handle_file_type(file_type: Union[FileType, str]) -> FileType:
    if isinstance(file_type, FileType):
        return file_type
    elif isinstance(file_type, str):
        try:
            return FileType[file_type]
        except KeyError:
            raise ValueError(f"ERROR : invalid format : {file_type}")
    else:
        raise ValueError(f"ERROR : invalid format : {file_type}")


def handle_files_types(
        file_type_s: Optional[Union[FileType, str, Iterable[Union[FileType, str]]]]
) -> Optional[Set[str]]:
    if file_type_s is None:
        return None

    if isinstance(file_type_s, str):
        file_type_s = FileType[file_type_s]

    if isinstance(file_type_s, FileType):
        return file_type_s.value

    if isinstance(file_type_s, Iterable):
        file_type_s = [handle_file_type(file_type) for file_type in file_type_s]

    return set(
        value for file_type in file_type_s for value in file_type.value
    )


def file_finder(
        path: Union[str, Path],
        *args,
        deep: int = 4,
        file_type_s: Optional[Union[FileType, str, Iterable[Union[FileType, str]]]] = None,
        file_values: Optional[Set[str]] = None,
        only_stems: Optional[Set[str]] = None,
        first_pass: bool = True,
        **kwargs
) -> Generator[Path, None, None]:
    """
    Find files in a directory and its subdirectories, with optional filtering by file type, file values, and file stems.
    Will not traverse symlinks.

    :param path: Path to the directory to search in.
    :param deep: Maximum depth to search in. -1 means infinite depth but is not recommended, as it would try recursively to find files in all subdirectories.
    :param file_type_s: File type to search for. Can be a string or a list of strings.
    :param file_values: Set of file values to search for. Can be a string or a list of strings.
    :param only_stems: Set of file stems to search for. Can be a string or a list of strings.
    :param first_pass: If True, the function will check the path and deep parameters.
    """
    if first_pass:
        if isinstance(path, str):
            path = Path(path)
        elif not isinstance(path, Path):
            raise ValueError(f"ERROR : invalid path : {path}")

        if isinstance(deep, str):
            try:
                deep = int(deep)
            except ValueError:
                raise ValueError(f"ERROR : invalid deepness treshold : {deep}")
        elif not isinstance(deep, int):
            raise ValueError(f"ERROR : invalid deepness treshold : {deep}")

        if file_values is None:
            file_values = handle_files_types(file_type_s)
        else:
            assert all(isinstance(fv, str) for fv in file_values), "ERROR : file_values must be a set of strings"

    for file in path.glob("*"):
        if file.is_dir():
            if deep == -1:
                yield from file_finder(
                    file,
                    deep=deep,
                    file_values=file_values,
                    only_stems=only_stems,
                    first_pass=False,
                )
            elif deep > 0:
                yield from file_finder(
                    file,
                    deep=deep - 1,
                    file_values=file_values,
                    only_stems=only_stems,
                    first_pass=False,
                )
        elif file_values is None or file.suffix.lower() in file_values:
            if only_stems is not None:
                if file.stem in only_stems or any(file.stem.startswith(stem) for stem in only_stems):
                    yield file
            else:
                yield file


def how_many_files(
        path: str | Path,
        **kwargs
) -> int:
    """
    Uses `file_finder` to count the number of files in a directory and its subdirectories.
    :param path: Path to the directory to search in.
    :param kwargs: Optional arguments to pass to `file_finder`. (See `file_finder` for details.)
    """
    return sum(1 for _ in file_finder(path, **kwargs))
