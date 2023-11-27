import io
import re
from typing import List

from europarser.models import Pivot
from europarser.transformers.transformer import Transformer


class IramuteqTransformer(Transformer):
    banned_keys = {"texte", "complement", "date", "epoch"}
    def __init__(self):
        super(IramuteqTransformer, self).__init__()

    def transform(self, pivot_list: List[Pivot]) -> str:
        with io.StringIO() as f:
            for pivot in pivot_list:
                dic = pivot.dict(exclude=self.banned_keys)
                f.write(f"""**** {' '.join([f"*{k}_{self._format_value(str(v))}" for k,v in dic.items()])}\n""")
                f.write(pivot.texte)
                f.write('\n\n')
            return f.getvalue()

    @staticmethod
    def _format_value(value: str):
        value = re.sub(r"[éèê]", "e", value)
        value = re.sub(r"ô", "o", value)
        value = re.sub(r"à", "a", value)
        value = re.sub(r"œ", "oe", value)
        value = re.sub(r"[ïîì]", "i", value)
        value = re.sub(r"""[-\[\]'":().=?!,;<>«»—^*\\/|]""", ' ', value)
        return ''.join([w.capitalize() for w in value.split(' ')])

