from typing import List

from ..models import Pivot, TransformerOutput
from ..transformers.transformer import Transformer

import polars as pl


class CSVTransformer(Transformer):
    def __init__(self):
        super(CSVTransformer, self).__init__()
        self.output_type = "csv"
        self.output = TransformerOutput(data=None, output=self.output_type, filename=f'{self.name}_output.{self.output_type}')

    def transform(self, pivot_list: List[Pivot]) -> TransformerOutput:
        try:
            df = pl.DataFrame([p.model_dump() for p in pivot_list])
            self.output.data = df.write_csv()
            return self.output
        except Exception as e:
            print(self.__class__.__name__, e)
            raise
            
