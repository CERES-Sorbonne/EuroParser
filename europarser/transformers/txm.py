import io
import re
import xml.dom.minidom as dom
from xml.sax.saxutils import escape
from typing import List

from europarser.models import Pivot, TransformerOutput
from europarser.transformers.transformer import Transformer


class TXMTransformer(Transformer):
    def __init__(self):
        super(TXMTransformer, self).__init__()
        self.output_type = "xml"
        self.output = TransformerOutput(data=None, output=self.output_type,
                                        filename=f'{self.name}_output.{self.output_type}')

    def transform(self, pivot_list: List[Pivot]) -> TransformerOutput:
        with io.StringIO() as f:
            f.write("<corpus>")

            for pivot in pivot_list:
                # print(pivot)
                parsed = escape(pivot.texte.strip())
                line = f"""\
                <article\
                titre="{re.sub('"', "'", escape(pivot.titre))}"\
                date="{escape(pivot.date)}" journal="{escape(pivot.journal)}"\
                annee="{pivot.annee}"\
                mois="{pivot.mois}"\
                jour="{pivot.jour}"\
                journal_clean="{escape(pivot.journal_clean)}"\
                keywords="{escape(pivot.keywords)}"\
                langue="{escape(pivot.langue)}\
                ">"""
                f.write(line)
                f.write(parsed)
                f.write("</article>")
            f.write("</corpus>")
            self.output.data = dom.parseString(f.getvalue()).toprettyxml()
            return self.output
