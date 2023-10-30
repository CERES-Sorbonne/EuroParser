from typing import List

from europarser.models import Pivot
from europarser.transformers.transformer import Transformer

import pandas as pd


class CSVTransformer(Transformer):
    def __init__(self):
        super(CSVTransformer, self).__init__()

    def transform(self, pivot_list: List[Pivot]) -> str:
        df = pd.DataFrame.from_records([p.dict() for p in pivot_list])
        return df.to_csv(sep=",", index=False)
            
