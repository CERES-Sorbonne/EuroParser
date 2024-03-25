# Europarser

[![PyPI - Version](https://img.shields.io/pypi/v/europarser.svg)](https://pypi.org/project/europarser)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/europarser.svg)](https://pypi.org/project/europarser)

Parsing press articles to extract content and transform it into analysis formats such as TXM or Iramuteq

-----

**Table of Contents**

- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Installation
### PyPi
Europarser is available on PyPi, you can install it with pip using the following command:
```bash
pip install europarser
```
You can then check that the installation went well by running the `europarser --version` command
Once installed, you can launch the graphical interface with the `europarser` command.

### Docker
```bash
docker run -p 8000:8000 --name europarser ceressorbonne/europarser
```
The server will be accessible on [localhost:8000](http://localhost:8000), you can also specify another port as follows:
```bash
docker run -p [desired port]:8000 --name europarser ceressorbonne/europarser
```

### Development
To install Europarser in development mode, you can clone the git repository and install the dependencies with pip:
```bash
git clone https://github.com/CERES-Sorbonne/EuropressParser.git
cd EuropressParser
pip install -e .
```


## Usage
#### Basic Usage
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

### Usage as an API
1) Install the package
```bash
pip install europarser
```

2) Start the server with the following command
```bash
europarser [--host HOST] [--port PORT]
```

3) Go to [localhost:8000](http://localhost:8000) (by default) to access the API interface

### Usage from the command line
1) Install the package
```bash
pip install europarser
```

2) Use the following command to parse a folder
```bash
europarser-cli --folder /path/to/your/articles --output [one of "json", "txm", "iramuteq", "csv", "stats", "processed_stats", "plots", "markdown"] [--output other_output] [--minimal-support-kw 5] [--minimal-support-authors 2] [--minimal-support-journals 8] [--minimal-support-dates 3]
```

#### Example
```bash
europarser-cli --folder /path/to/your/articles --output json --output txm --minimal-support-kw 5 --minimal-support-authors 2 --minimal-support-journals 8 --minimal-support-dates 3
```

## License

`europarser` is distributed under the terms of the [AGPLv3](https://www.gnu.org/licenses/agpl-3.0.html) license.
