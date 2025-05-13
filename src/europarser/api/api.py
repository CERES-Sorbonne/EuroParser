import logging
import os
import zipfile
from io import StringIO, BytesIO
from pathlib import Path
from typing import Annotated  # , Optional
from uuid import uuid4
from zipfile import ZipFile
from datetime import date

from fastapi import FastAPI, UploadFile, Request, HTTPException, File, Form  # , Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import FileResponse, StreamingResponse
from filedetect import FileDetect

from europarser import FileToTransform, pipeline
from europarser.api.utils import get_mimetype
from europarser.models import TransformerOutput, Params, Outputs

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


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse('index.html', {'request': request, 'host': host})


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
        file: Annotated[UploadFile, File(...)],
):
    tmp_folder = temp_dir / uuid
    if not tmp_folder.exists():
        raise HTTPException(status_code=404, detail="UUID not found")
    with open(tmp_folder / file.filename, "wb") as f:
        f.write(file.file.read())
    return {"file": file.filename}


@app.post("/convert")
async def convert(
        uuid: Annotated[str, Form(...)],
        output: Annotated[list[Outputs], Form(...)],
        # params: Annotated[dict, Form(...)],
        filter_keywords: Annotated[bool, Form(...)] = None,
        filter_lang: Annotated[bool, Form(...)] = None,
        minimal_support: Annotated[int, Form(...)] = None,
        minimal_support_kw: Annotated[int, Form(...)] = None,
        minimal_support_journals: Annotated[int, Form(...)] = None,
        minimal_support_authors: Annotated[int, Form(...)] = None,
        minimal_support_dates: Annotated[int, Form(...)] = None,
        txm_mode: Annotated[str, Form(...)] = None,
        keep_p_tags: Annotated[bool, Form(...)] = None,
):
    folder = temp_dir / uuid

    if not folder.exists():
        raise HTTPException(status_code=404, detail="UUID not found")

    to_process_files = FileDetect.find(path=folder, suffixes={".html", ".json"}).result
    all_files = FileDetect.find(path=folder).result

    if len(to_process_files) == 0:
        raise HTTPException(status_code=404, detail="No files found")
    elif len(to_process_files) != len(all_files):
        raise HTTPException(status_code=400, detail=f"Only HTML files are supported.\nList of files :{all_files}")

    # parse all files
    try:
        to_process = [FileToTransform(name=f.name, file=f.read_text(encoding="utf-8")) for f in to_process_files]
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid File Provided")

    try:
        params = Params(
            **{k: v for k, v in {
                "filter_keywords": filter_keywords,
                "filter_lang": filter_lang,
                "minimal_support": minimal_support,
                "minimal_support_kw": minimal_support_kw,
                "minimal_support_journals": minimal_support_journals,
                "minimal_support_authors": minimal_support_authors,
                "minimal_support_dates": minimal_support_dates,
                "txm_mode": txm_mode,
                "keep_p_tags": keep_p_tags,
            }.items() if v is not None}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        # process result
        results: list[TransformerOutput] = pipeline(to_process, output, params)
    except NotImplementedError as e:
        raise HTTPException(status_code=500, detail=f"A unimplemented output was requested\nError:{e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # if only one output was required let's return a single file
    if len(results) == 1:
        result = results[0]

        if isinstance(result.data, StringIO) or isinstance(result.data, BytesIO):
            pass
        elif not isinstance(result.data, bytes):
            result.data = StringIO(result.data)
        else:
            result.data = BytesIO(result.data)

        return StreamingResponse(
            result.data,
            media_type=get_mimetype(result.output),
            headers={
                'Content-Disposition': f"attachment; filename=EuroParser_{date.today().strftime('%d-%m-%Y')}_{result.filename}"}
        )

    # else let's create a zip with all files
    zip_io = BytesIO()
    with ZipFile(zip_io, mode='w', compression=zipfile.ZIP_DEFLATED) as temp_zip:
        for result in results:
            logger.info(f"Adding {result.filename} to zip")
            if result.output == "zip":
                name = Path(result.filename).stem  # get filename without extension (remove .zip basically)
                logger.info(f"Zip file detected, extracting {name}")
                with ZipFile(BytesIO(result.data), mode='r') as z:
                    for f in z.namelist():
                        temp_zip.writestr(f"{name}/{f}", z.read(f))
                continue

            temp_zip.writestr(f"{result.filename}", result.data)

    zip_io.seek(0)
    return StreamingResponse(
        zip_io,
        media_type="application/zip",
        headers={'Content-Disposition': f'attachment; filename=EuroParser_{date.today().strftime("%d-%m-%Y")}.zip'}
    )


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
