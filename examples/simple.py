import os.path

from europarser import pipeline, FileToTransform

if __name__ == "__main__":
    with open(os.path.join(os.path.dirname(__file__), 'resources', '1.HTML'), 'r') as f:
        xml_res = pipeline([FileToTransform(name="test", file=f.read())], output="txm")
