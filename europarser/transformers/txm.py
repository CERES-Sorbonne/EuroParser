import io
import re
import xml.dom.minidom as dom
from xml.sax.saxutils import escape
from typing import List

from europarser.models import Pivot
from europarser.transformers.transformer import Transformer


class TXMTransformer(Transformer):
    def __init__(self):
        super(TXMTransformer, self).__init__()

    def transform(self, pivot_list: List[Pivot]) -> str:
        with io.StringIO() as f:
            f.write("<corpus>")
            
            for pivot in pivot_list:
                print(pivot)
                parsed = escape(pivot.texte.strip())
                line = f"""<article titre="{re.sub('"', "'", escape(pivot.titre))}" date="{escape(pivot.date)}" journal="{escape(pivot.journal)}" journal_clean="{escape(pivot.journal_clean)}" keywords="{escape(pivot.keywords)}">"""
                f.write(line)
                f.write(parsed)
                f.write("</article>")
            f.write("</corpus>")
            return dom.parseString(f.getvalue()).toprettyxml()
