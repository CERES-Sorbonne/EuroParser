from io import BytesIO
from typing import List

from ..models import Pivot, TransformerOutput
from ..transformers.transformer import Transformer

import polars as pl

class ExcelTransformer(Transformer):
    def __init__(self):
        super(ExcelTransformer, self).__init__()
        self.output_type = "excel"
        self.output = TransformerOutput(data=None, output=self.output_type,
                                        filename=f'{self.name}_output.xlsx')

    def transform(self, pivot_list: List[Pivot]) -> TransformerOutput:
        try:
            df = pl.DataFrame([p.model_dump() for p in pivot_list])
            with BytesIO() as output:
                df.write_excel(output)
                output.seek(0)
                self.output.data = output.read()
            return self.output
        except Exception as e:
            print(self.__class__.__name__, e)
            raise
