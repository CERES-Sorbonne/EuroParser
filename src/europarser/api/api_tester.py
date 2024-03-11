from pathlib import Path
import requests

from concurrent.futures import ThreadPoolExecutor

from ..models import FileToTransform, Params

# server = "https://ceres.huma-num.fr/europarser"
server = "http://localhost:8000"

file = Path("../examples/resources/1.HTML")

output = ["json"]

params = Params()

stress = 32


def send_file(file, output: list[str], params: Params) -> int:
    url = f"{server}/upload"
    data = {'output': output, 'params': params}
    r = requests.post(url, files=file, data=data)
    return r.status_code


if __name__ == "__main__":
    with open(file, 'r', encoding='utf-8') as f:
        # file = FileToTransform(name=file.name, file=f.read())
        file = f.read()
        file = {'files': file}

    with ThreadPoolExecutor(max_workers=stress) as executor:
        futures = [executor.submit(send_file, file, output, params) for _ in range(stress)]
        for future in futures:
            print(future.result())
