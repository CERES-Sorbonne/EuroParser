import io
import re
import xml.dom.minidom as dom
from xml.sax.saxutils import quoteattr, escape
from typing import List

from ..models import Pivot, TransformerOutput
from ..transformers.transformer import Transformer


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
                pivot_dict = {
                    "id": pivot.id,
                    "titre": pivot.titre,
                    "date": pivot.date,
                    "journal": pivot.journal,
                    "auteur": pivot.auteur,
                    "annee": pivot.annee,
                    "mois": pivot.mois,
                    "jour": pivot.jour,
                    "journalClean": pivot.journal_clean,
                    "keywords": ', '.join(pivot.keywords),
                    "langue": pivot.langue,
                    "url": pivot.url,
                }
                f.write("<text ")
                for key, value in pivot_dict.items():
                    if value:
                        f.write(f"{key}={quoteattr(str(value))} ")
                f.write(f"> {escape(pivot.texte.strip()) if pivot.texte else ''} </text>\n")

            f.write("</corpus>")
            self.output.data = dom.parseString(f.getvalue()).toprettyxml()
            return self.output
