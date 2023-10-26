import io
# import logging
import os
import zipfile
from enum import Enum
from typing import List  # , Optional

from fastapi import FastAPI, UploadFile, Request, Form, HTTPException, File  # , Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from europarser.models import FileToTransform  # , Output
from europarser.transformers.pipeline import pipeline
from europarser_api.utils import get_mimetype

root_dir = os.path.dirname(__file__)
host = os.getenv('EUROPARSER_SERVER', '')
app = FastAPI()

app.mount("/static", StaticFiles(directory=os.path.join(root_dir, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(root_dir, "templates"))


class Outputs(str, Enum):
    json = "json"
    txm = "txm"
    iramuteq = "iramuteq"
    gephi = "gephi"
    csv = "csv"
    stats = "stats"
    processed_stats = "processed_stats"
    plots = "plots"


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse('main.html', {'request': request, 'host': host})


@app.post("/upload")
async def handle_files(files: List[UploadFile] = File(...), output: List[Outputs] = Form(...)):
    if len(files) == 1 and files[0].filename == "":
        raise HTTPException(status_code=400, detail="No File Provided")
    # parse all files
    try:
        to_process = [FileToTransform(name=f.filename, file=f.file.read().decode('utf-8')) for f in files]
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid File Provided")
    # process result
    results = pipeline(to_process, output)

    if len(results) == 1:
        result = results[0]
        output = output[0]

        if not isinstance(result['data'], bytes):
            result['data'] = io.StringIO(result)
        else:
            result['data'] = io.BytesIO(result)


        return StreamingResponse(
            result['data'],
            media_type=get_mimetype(result['output']),
            headers={'Content-Disposition': f"attachment; filename={output.value}.{result['type']}"}
        )

    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, mode='w', compression=zipfile.ZIP_DEFLATED) as temp_zip:
        for result in results:
            out = result['output']
            res = result['data']
            type_ = result['type']
            print(f"{out = } {type_ = }")
            if type_ == "zip":
                temp_zip.mkdir(out.value)
                with zipfile.ZipFile(io.BytesIO(res), mode='r') as z:
                    for f in z.namelist():
                        temp_zip.writestr(f"{out.value}/{f}", z.read(f))
                continue

            temp_zip.writestr(f"{out.value}.{type_}", res)

    zip_io.seek(0)
    return StreamingResponse(
        zip_io,
        media_type="application/zip",
        headers={'Content-Disposition': 'attachment; filename=result.zip'}
    )
