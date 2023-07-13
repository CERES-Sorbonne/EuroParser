# EuropressParser
Parsing d'articles de presse pour extraire le contenu et le transformer en des formats d'analyse comme TXM ou Iramuteq

# Installation basique
```bash 
python setup.py install
```

# Usage basique
```python
from europarser import process

res = process("<html> Valid HTML Europress string ... </html>", output="txm")
```

# Autres usages
Voir dans le dossier examples

# Installation sous forme d'API
1) Installer tout d'abord comme pour l'installation basique
2) ```bash
    pip install -r requirements-api.txt
    ```
3) ```bash
    uvicorn europarser_api.api:app --reload
    ```
4) Aller sur [localhost:8000](http://localhost:8000)

