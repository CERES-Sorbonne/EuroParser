from europarser.models import Pivot

def minimal(pivots : List[Pivot], taillemin : int = 300) -> List[Pivot]:
    return [e for e in pivots if "This extract may not display a well formed paragraph" not in e["texte"] and len(e["texte"]) > taillemin] 
