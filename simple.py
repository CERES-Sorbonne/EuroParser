import os.path
import json

from europarser import process

output = "txm"

if __name__ == "__main__":
  with open(os.path.join(os.path.dirname(__file__), 'examples/resources', '1.HTML'), 'r') as f:
    xml_res = process(f.read(), output=output, lang=True)
    
    with open(f"res.{output}",'w',encoding='utf-8') as f:
      f.write(xml_res[0])
