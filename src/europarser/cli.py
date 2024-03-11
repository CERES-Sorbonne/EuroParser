from pathlib import Path
from argparse import ArgumentParser

from europarser.main import main
from europarser.models import Params

parser = ArgumentParser()

parser.add_argument("-f", "--folder", help="Folder to process", type=str)
parser.add_argument("-o", "--output", help="Outputs to generate", nargs="+", type=str)
parser.add_argument("--support-kw", help="Minimal support for keywords", type=int)
parser.add_argument("--support-authors", help="Minimal support for authors", type=int)
parser.add_argument("--support-journals", help="Minimal support for journals", type=int)
parser.add_argument("--support-dates", help="Minimal support for dates", type=int)
parser.add_argument("--support", help="Minimal support for all", type=int)
parser.add_argument("--filter-keywords", help="Filter keywords", type=bool, default=False)
parser.add_argument("--filter-lang", help="Filter language", type=bool, default=False)

if __name__ == '__main__':
    args = parser.parse_args()
    folder = Path(args.folder)
    outputs = args.output
    params = Params(
        minimal_support_kw=args.support_kw,
        minimal_support_authors=args.support_authors,
        minimal_support_journals=args.support_journals,
        minimal_support_dates=args.support_dates,
        minimal_support=args.support or 1,
        filter_keywords=args.filter_keywords,
        filter_lang=args.filter_lang
    )
    main(folder, outputs, params=params)
