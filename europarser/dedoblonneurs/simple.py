import contextlib, re

from europarser.models import Pivot
from tqdm.auto import tqdm

def doublon_simple(pivot: Pivot) -> Pivot:
    temppivot = pivot.copy()
    ids = {}
    for e in tqdm(pivot, desc="Dédoublonage simple", leave = True):
    #Le split permet de virer les éditions ainsi le tonronto news (final) et le toronto news (morning) ne sont pas 
    #discriminés (de meme pour tous les journaux)
        id_ =  ' '.join([e["titre"], re.split(" \(| -| no. | \d|  | ;", e["journal"])[0], e["date"]])
        if id_ in ids:
            with contextlib.suppress(Exception):
                temppivot.remove(e)
        else:
            ids.add(id_)