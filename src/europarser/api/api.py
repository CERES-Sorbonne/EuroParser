import logging
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Annotated  # , Optional
from uuid import uuid4

from fastapi import FastAPI, UploadFile, Request, HTTPException, File  # , Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import FileResponse

# root_dir = os.path.dirname(__file__)
root_dir = Path(__file__).parent
host = os.getenv('EUROPARSER_SERVER', '')
temp_dir = Path(os.getenv('EUROPARSER_TEMP_DIR', '/tmp/europarser'))
temp_dir.mkdir(parents=True, exist_ok=True)
app = FastAPI()

app.mount("/static", StaticFiles(directory=root_dir / "static"), name="static")
templates = Jinja2Templates(directory=root_dir / "templates")
favicon_path = root_dir / "static/favicon.ico"

logger = logging.getLogger("europarser_api.api")
logger.setLevel(logging.DEBUG)


class Outputs(str, Enum):
    json = "json"
    txm = "txm"
    iramuteq = "iramuteq"
    gephi = "gephi"
    csv = "csv"
    excel = "excel"
    stats = "stats"
    processed_stats = "processed_stats"
    plots = "plots"
    markdown = "markdown"


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse('new_wui.html', {'request': request, 'host': host})


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(favicon_path)


@app.get("/create_file_upload_url")
async def create_file_upload_url():
    uuid_ = uuid4().hex
    tmp_folder = temp_dir / uuid_
    if tmp_folder.exists():
        raise HTTPException(status_code=500, detail="UUID collision")
    tmp_folder.mkdir()
    print(f"Created folder {tmp_folder}")
    return {"uuid": uuid_, "upload_url": f"/upload/{uuid_}"}


@app.post("/upload/{uuid}")
async def upload_file(
        uuid: str,
        file: Annotated[list[UploadFile], File(...)],
):
    tmp_folder = temp_dir / uuid
    if not tmp_folder.exists():
        raise HTTPException(status_code=404, detail="UUID not found")
    with open(tmp_folder / file.filename, "wb") as f:
        f.write(file.file.read())
    return {"file": file.filename}


# @app.post("/upload")
# async def handle_files(files: Annotated[list[UploadFile], File(...)],
#                        output: Annotated[list[Outputs], Form(...)],
#                        params: Annotated[Params, Depends()]):
#     if len(files) == 1 and files[0].filename == "":
#         raise HTTPException(status_code=400, detail="No File Provided")
#     # parse all files
#     try:
#         to_process = [FileToTransform(name=f.filename, file=f.file.read().decode('utf-8')) for f in files]
#     except UnicodeDecodeError:
#         raise HTTPException(status_code=400, detail="Invalid File Provided")
#
#     # process result
#     results: list[TransformerOutput] = pipeline(to_process, output, params)
#
#     # if only one output was required let's return a single file
#     if len(results) == 1:
#         result = results[0]
#
#         if isinstance(result.data, io.StringIO) or isinstance(result.data, io.BytesIO):
#             pass
#         elif not isinstance(result.data, bytes):
#             result.data = io.StringIO(result.data)
#         else:
#             result.data = io.BytesIO(result.data)
#
#         return StreamingResponse(
#             result.data,
#             media_type=get_mimetype(result.output),
#             headers={'Content-Disposition': f"attachment; filename={result.filename}"}
#         )
#
#     # else let's create a zip with all files
#     zip_io = io.BytesIO()
#     with zipfile.ZipFile(zip_io, mode='w', compression=zipfile.ZIP_DEFLATED) as temp_zip:
#         for result in results:
#             logger.info(f"Adding {result.filename} to zip")
#             if result.output == "zip":
#                 name = Path(result.filename).stem  # get filename without extension (remove .zip basically)
#                 logger.info(f"Zip file detected, extracting {name}")
#                 with zipfile.ZipFile(io.BytesIO(result.data), mode='r') as z:
#                     for f in z.namelist():
#                         temp_zip.writestr(f"{name}/{f}", z.read(f))
#                 continue
#
#             temp_zip.writestr(f"{result.filename}", result.data)
#
#     zip_io.seek(0)
#     return StreamingResponse(
#         zip_io,
#         media_type="application/zip",
#         headers={'Content-Disposition': 'attachment; filename=result.zip'}
#     )


def main():
    from argparse import ArgumentParser

    import uvicorn

    parser = ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", default=8000, help="Port to bind to", type=int)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
