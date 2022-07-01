from europarser.models import Pivot

def minimal(pivot : Pivot, taillemin : int) -> Pivot:
    return [e for e in pivot if "This extract may not display a well formed paragraph" not in e["texte"] and len(e["texte"]) > taillemin] 
