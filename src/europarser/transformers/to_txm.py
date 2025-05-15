import xml.dom.minidom as dom
import zipfile
from io import BytesIO, StringIO
from typing import List, Optional, Any
from xml.sax.saxutils import quoteattr, escape

from ..models import Pivot, TransformerOutput, TXM_MODE, Params
from ..transformers.transformer import Transformer
from ..utils import super_writestr


class TXMTransformer(Transformer):
    XML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n'

    def __init__(self, params: Optional[Params] = None, **kwargs: Optional[Any]):
        super().__init__(params, **kwargs)
        self.output_type = "zip" if self.params.txm_mode == TXM_MODE.MULTIPLE_FILES else "xml"
        self.output = TransformerOutput(
            data=None, output=self.output_type, filename=f'{self.name}_output.{self.output_type}'
        )

    def clean_name(self, pivot: Pivot, i=None) -> str:
        return f"{pivot.annee}_{pivot.mois}_{pivot.jour}_{pivot.journal_clean.replace(' ', '-')}_{self.clean_string(pivot.titre)[:50]}{f'_{i}' if i else ''}.xml"

    def do_one_article(self, pivot: Pivot, stream, pb=False) -> None:
        pivot_dict = {
            "identifiant": pivot.identifiant,
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
        stream.write("<text ")
        for key, value in pivot_dict.items():
            if value:
                stream.write(f"{key}={quoteattr(str(value))} ")

        cleaned_string = escape(pivot.texte.strip().replace('\n', '<lb/>\n')) if pivot.texte else ''
        stream.write(f"> {cleaned_string} </text>\n")
        if pb:
            stream.write("<pb/>\n")

    def transform(self, pivot_list: List[Pivot], mode=None) -> TransformerOutput:
        try:
            if mode:
                self.params.txm_mode = mode
                self.output_type = "zip" if self.params.txm_mode == TXM_MODE.MULTIPLE_FILES else "xml"
                self.output = TransformerOutput(
                    data=None, output=self.output_type, filename=f'{self.name}_output.{self.output_type}'
                )

            if self.params.txm_mode in {TXM_MODE.LEGACY, TXM_MODE.ONE_FILE_PB}:
                with StringIO() as f:
                    f.write(self.XML_HEADER + "<corpus>\n")
                    length = len(pivot_list)
                    for i, pivot in enumerate(pivot_list):
                        if i + 1 == length:
                            self.do_one_article(pivot, f)
                        else:
                            self.do_one_article(pivot, f, pb=self.params.txm_mode == TXM_MODE.ONE_FILE_PB)
                    f.write("</corpus>")
                    self.output.data = dom.parseString(f.getvalue()).toprettyxml()
            elif self.params.txm_mode == TXM_MODE.MULTIPLE_FILES:
                with BytesIO() as zio:
                    with zipfile.ZipFile(zio, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                        for pivot in pivot_list:


                            with StringIO() as f:
                                f.write(self.XML_HEADER)
                                self.do_one_article(pivot, f)
                                try:
                                    super_writestr(
                                        z,
                                        self.clean_name(pivot),
                                        dom.parseString(f.getvalue()).toprettyxml()
                                    )
                                except Exception as e:
                                    pass
                                    raise e

                    self.output.data = zio.getvalue()
            else:
                raise ValueError(f"Invalid TXM mode: {self.params.txm_mode}")

            return self.output
        except Exception as e:
            print(self.__class__.__name__, e)
            raise