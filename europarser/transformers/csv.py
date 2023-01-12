import io
import re
import xml.dom.minidom as dom
from xml.sax.saxutils import escape
from typing import List

from europarser.models import Pivot
from europarser.transformers.transformer import Transformer

import pandas as pd

class CSVTransformer(Transformer):
    def __init__(self):
        super(CSVTransformer, self).__init__()

    def transform(self, pivot_list: List[Pivot]) -> str:
        with io.StringIO() as f:
            f.write("<corpus>")
            csv = []
            for pivot in pivot_list:
              csv.append([pivot.journal_clean,pivot.journal,pivot.date,pivot.titre,pivot.texte,pivot.keywords])
            df =  pd.DataFrame(csv,columns=["journal_clean","journal","date","titre","texte","keywords"])
            return df.to_csv(sep=",",index=False)
            
