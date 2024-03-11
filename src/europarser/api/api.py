import io
import logging
import os
import zipfile
from enum import Enum
from pathlib import Path
from typing import List, Annotated  # , Optional

from fastapi import FastAPI, UploadFile, Request, Form, HTTPException, File, Depends  # , Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from ..models import FileToTransform, TransformerOutput, Params  # , Output
from .. import pipeline
from .utils import get_mimetype

root_dir = os.path.dirname(__file__)
host = os.getenv('EUROPARSER_SERVER', '')
app = FastAPI()

app.mount("/static", StaticFiles(directory=os.path.join(root_dir, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(root_dir, "templates"))

logger = logging.getLogger("europarser_api.api")
logger.setLevel(logging.DEBUG)


class Outputs(str, Enum):
    json = "json"
    txm = "txm"
    iramuteq = "iramuteq"
    gephi = "gephi"
    csv = "csv"
    stats = "stats"
    processed_stats = "processed_stats"
    plots = "plots"
    markdown = "markdown"


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse('main.html', {'request': request, 'host': host})


@app.post("/upload")
async def handle_files(files: Annotated[list[UploadFile], File(...)],
                       output: Annotated[list[Outputs], Form(...)],
                       params: Annotated[Params, Depends()]):
    if len(files) == 1 and files[0].filename == "":
        raise HTTPException(status_code=400, detail="No File Provided")
    # parse all files
    try:
        to_process = [FileToTransform(name=f.filename, file=f.file.read().decode('utf-8')) for f in files]
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid File Provided")

    # process result
    results: list[TransformerOutput] = pipeline(to_process, output, params)

    # if only one output was required let's return a single file
    if len(results) == 1:
        result = results[0]

        if isinstance(result.data, io.StringIO) or isinstance(result.data, io.BytesIO):
            pass
        elif not isinstance(result.data, bytes):
            result.data = io.StringIO(result.data)
        else:
            result.data = io.BytesIO(result.data)

        return StreamingResponse(
            result.data,
            media_type=get_mimetype(result.output),
            headers={'Content-Disposition': f"attachment; filename={result.filename}"}
        )

    # else let's create a zip with all files
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, mode='w', compression=zipfile.ZIP_DEFLATED) as temp_zip:
        for result in results:
            logger.info(f"Adding {result.filename} to zip")
            if result.output == "zip":
                name = Path(result.filename).stem  # get filename without extension (remove .zip basically)
                logger.info(f"Zip file detected, extracting {name}")
                with zipfile.ZipFile(io.BytesIO(result.data), mode='r') as z:
                    for f in z.namelist():
                        temp_zip.writestr(f"{name}/{f}", z.read(f))
                continue

            temp_zip.writestr(f"{result.filename}", result.data)

    zip_io.seek(0)
    return StreamingResponse(
        zip_io,
        media_type="application/zip",
        headers={'Content-Disposition': 'attachment; filename=result.zip'}
    )

def main():
    import uvicorn
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", default=8000, help="Port to bind to", type=int)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
