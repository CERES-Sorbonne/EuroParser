import io
import os
import zipfile
from enum import Enum
from typing import Optional, List
import gzip

from fastapi import FastAPI, UploadFile, Request, Form, HTTPException, File, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from europarser.models import FileToTransform, Output
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
    result, result_type = pipeline(to_process, output)

    if len(result) == 1:
        result = result[0]
        result_type = result_type[0]
        output = output[0]
        print(result_type)
        return StreamingResponse(
            io.StringIO(result),
            media_type=get_mimetype(result_type),
            headers={'Content-Disposition': f'attachment; filename={output.value}.{result_type}'}
        )

    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, mode='w', compression=zipfile.ZIP_DEFLATED) as temp_zip:
        for out, res, type_ in zip(output, result, result_type):
            temp_zip.writestr(f"{out.value}.{type_}", res)
    zip_io.seek(0)
    return StreamingResponse(
        zip_io,
        media_type="application/zip",
        headers={'Content-Disposition': 'attachment; filename=result.zip'}
    )
