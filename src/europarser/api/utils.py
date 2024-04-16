from typing import Literal

from .. import OutputFormat

MimeType = Literal["text/csv", "application/json", "text/plain", "text/xml", "application/vnd.ms-excel"]


def get_mimetype(output_type: OutputFormat) -> MimeType:
    if output_type == "csv":
        return "text/csv"
    elif output_type == "json":
        return "application/json"
    elif output_type == "txt":
        return "text/plain"
    elif output_type == "xml":
        return "text/xml"
    elif output_type == "excel":
        return "application/vnd.ms-excel"
    else:
        raise ValueError(f"Unknown output type: {output_type}")
