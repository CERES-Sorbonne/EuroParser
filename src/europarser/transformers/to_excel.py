from io import BytesIO
from typing import List

from ..models import Pivot, TransformerOutput
from ..transformers.transformer import Transformer

import pandas as pd
from pandas import ExcelWriter


class ExcelTransformer(Transformer):
    def __init__(self):
        super(ExcelTransformer, self).__init__()
        self.output_type = "excel"
        self.output = TransformerOutput(data=None, output=self.output_type,
                                        filename=f'{self.name}_output.xlsx')

    def transform(self, pivot_list: List[Pivot]) -> TransformerOutput:
        df = pd.DataFrame.from_records([p.model_dump() for p in pivot_list])
        with BytesIO() as output:
            df.to_excel(output, index=False)
            output.seek(0)
            self.output.data = output.read()
        return self.output

