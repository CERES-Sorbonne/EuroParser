import io
import os
from typing import Optional, List

from fastapi import FastAPI, UploadFile, Request, Form, HTTPException, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from europarser.models import FileToTransform, Output
from europarser.transformers.pipeline import pipeline
from europarser_api.utils import get_mimetype

root_dir = os.path.dirname(__file__)
app = FastAPI()

app.mount("/static", StaticFiles(directory=os.path.join(root_dir, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(root_dir, "templates"))


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse('main.html', {'request': request})


@app.post("/upload")
async def handle_files(files: List[UploadFile] = File(...), output: Optional[Output] = Form(...)):
    if len(files) == 1 and files[0].filename == "":
        raise HTTPException(status_code=400, detail="No File Provided")
    # parse all files
    try:
        to_process = [FileToTransform(name=f.filename, file=f.file.read().decode('utf-8')) for f in files]
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid File Provided")
    # process result
    result, result_type = pipeline(to_process, output)
    result_mimetype = get_mimetype(result_type)
    # stream result as file
    response = StreamingResponse(io.StringIO(result), media_type=result_mimetype)
    response.headers["Content-Disposition"] = f"attachment; filename=result.{result_type}"
    return response