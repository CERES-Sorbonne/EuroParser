# Europarser

[![PyPI - Version](https://img.shields.io/pypi/v/europarser.svg)](https://pypi.org/project/europarser)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/europarser.svg)](https://pypi.org/project/europarser)

Parsing d'articles de presse pour extraire le contenu et le transformer en des formats d'analyse comme TXM ou Iramuteq.

This readme is also available in [English](https://github.com/CERES-Sorbonne/EuroperssParser/blob/master/README_en.md)

-----

**Table des matières**

- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Installation

Vous aurez besoin soit de python soit de docker pour pouvoir utiliser Europarser sur votre ordinateur.

### Python
Europarser est disponible sur PyPi, vous pouvez l'installer avec pip à l'aide de la commande suivante:
```bash
pip install europarser
```
Vous pouvez ensuite vérifier que l'installation s'est bien passée en lançant europarser à l'aide de `europarser --api`

### Docker
```bash
docker run -p 8000:8000 --name europarser ceressorbonne/europarser
```
Le serveur sera accessible sur [localhost:8000](http://localhost:8000), vous pouvez également spécifier un autre port de la manière suivante:
```bash
docker run -p [port souhaité]:8000 --name europarser ceressorbonne/europarser
```

### Développement
Pour installer Europarser en mode développement, vous pouvez cloner le dépôt git et installer les dépendances avec pip:
```bash
git clone https://github.com/CERES-Sorbonne/EuropressParser.git
cd EuropressParser
pip install -e .
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

### Usage sous forme d'API web
1) Installez le package
    ```bash
    pip install europarser
    ```

2) Lancez le serveur avec la commande suivante
    ```bash
    europarser --api [--host HOST] [--port PORT]
    ```

3) Allez sur [localhost:8000](http://localhost:8000) (par défaut) pour accéder à l'interface de l'API

### Usage en ligne de commande
1) Installez le package
    ```bash
    pip install europarser
    ```

2) Utilisez la commande suivante pour parser un dossier
    ```bash
    europarser --folder /path/to/your/articles --output [one of "json", "txm", "iramuteq", "csv", "stats", "processed_stats", "plots", "markdown"] [--output other_output] [--minimal-support-kw 5] [--minimal-support-authors 2] [--minimal-support-journals 8] [--minimal-support-dates 3]
    ```

#### Exemple
```bash
europarser --folder /path/to/your/articles --output json --output txm --minimal-support-kw 5 --minimal-support-authors 2 --minimal-support-journals 8 --minimal-support-dates 3
```

## License

`europarser` est distribué sous les termes de la licence [AGPLv3](https://www.gnu.org/licenses/agpl-3.0.html).
