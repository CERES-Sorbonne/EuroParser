import json
from typing import List

from ..models import Pivot, TransformerOutput
from ..transformers.transformer import Transformer


class JSONTransformer(Transformer):
    def __init__(self):
        super(JSONTransformer, self).__init__()
        self.output_type = "json"
        self.output = TransformerOutput(data=None, output=self.output_type,
                                        filename=f'{self.name}_output.{self.output_type}')

    def transform(self, pivot_list: List[Pivot]) -> TransformerOutput:
        json_ver = json.dumps({i: article.model_dump() for i, article in enumerate(pivot_list)}, ensure_ascii=False, indent=4)
        self.output.data = json_ver
        return self.output

