# Europarser

[![PyPI - Version](https://img.shields.io/pypi/v/europarser.svg)](https://pypi.org/project/europarser)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/europarser.svg)](https://pypi.org/project/europarser)

Parsing d'articles de presse pour extraire le contenu et le transformer en des formats d'analyse comme TXM ou Iramuteq

-----

**Table of Contents**

- [Installation](#installation)
- [License](#license)

## Installation

```console
pip install europarser
```


## Usages
#### Usage basique
```python
from pathlib import Path

from europarser.main import main
from europarser.models import Params

folder = Path('/path/to/your/articles')
# As a list, you can choose between "json", "txm", "iramuteq", "csv", "stats", "processed_stats", "plots", "markdown" or any combination of them
outputs = ["json", "txm", "iramuteq", "csv", "stats", "processed_stats", "plots", "markdown"]
params = Params(
    minimal_support_kw=5,
    minimal_support_authors=2,
    minimal_support_journals=8,
    minimal_support_dates=3,
)

main(folder, outputs, params=params)
```

### Usage sous forme d'API
1) Installez le package
```console
pip install europarser
```

2) Lancez le serveur avec la commande suivante
```console
europarser-api [--host HOST] [--port PORT]
```

3) Allez sur [localhost:8000](http://localhost:8000) (par défaut) pour accéder à l'interface de l'API


## License

`europarser` est distribué sous les termes de la licence [AGPLv3](https://www.gnu.org/licenses/agpl-3.0.html).
