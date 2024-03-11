import io
from typing import List

from ..models import Pivot, TransformerOutput
from ..transformers.transformer import Transformer


class IramuteqTransformer(Transformer):
    banned_keys = {"texte", "complement", "date", "epoch"}

    def __init__(self):
        super(IramuteqTransformer, self).__init__()
        self.output_type = "txt"
        self.output = TransformerOutput(data=None, output=self.output_type,
                                        filename=f'{self.name}_output.{self.output_type}')

    def transform(self, pivot_list: List[Pivot]) -> TransformerOutput:
        with io.StringIO() as f:
            for pivot in pivot_list:
                dic = pivot.model_dump(exclude=self.banned_keys)
                f.write(f"""**** {' '.join([f"*{k}_{self._format_value(str(v))}" for k, v in dic.items()])}\n""")
                f.write(pivot.texte)
                f.write('\n\n')
            self.output.data = f.getvalue()
            return self.output
