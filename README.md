# EuropressParser
Parsing d'articles de presse pour extraire le contenu et le transformer en des formats d'analyse comme TXM ou Iramuteq

# Installation basique
```python setup.py install```

# Usage basique
```python
from europarser import process

res = process("<html> Valid HTML Europress string ... </html>", output="txm")
```

# Autres usages
Voir dans le dossier examples

# Installation sous forme d'API
1) Installer tout d'abord comme pour l'installation basique
2) `pip install -r requirements-api.txt`
3) `uvicorn europarser_api.api:app --reload`
4) Aller sur localhost:8000
