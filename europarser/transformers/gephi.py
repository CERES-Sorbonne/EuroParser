# from typing import List
#
# from europarser.models import Pivot
# from europarser.transformers.transformer import Transformer
#
# import pandas as pd
#
#
# class GephiTransformer(Transformer):
#     def __init__(self):
#         super(GephiTransformer, self).__init__()
#
#     def transform(self, pivot_list: List[Pivot], graph_type="skeletton") -> str:
#         pivot_list.sort(key=lambda x: x.date)
#         first_date = pivot_list[0].date
#         last_date = pivot_list[-1].date
#
#         return df.to_csv(sep=",", index=False)
