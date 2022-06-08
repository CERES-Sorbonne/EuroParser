import os.path

from europarser import process

if __name__ == "__main__":
    with open(os.path.join(os.path.dirname(__file__), 'resources', '1.HTML'), 'r') as f:
        xml_res = process(f.read(), output="txm")
