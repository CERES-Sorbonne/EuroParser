import os.path

from europarser import FileToTransform, pipeline

if __name__ == "__main__":
    with open(os.path.join(os.path.dirname(__file__), 'resources', '1.HTML'), 'r') as f:
        fake_file = FileToTransform(file=f.read(), name="fake_file_1")

    with open(os.path.join(os.path.dirname(__file__), 'resources', '1.HTML'), 'r') as f:
        fake_file_2 = FileToTransform(file=f.read(), name="fake_file_2")

    xml_res = pipeline([fake_file, fake_file_2], output="txm")
