from argparse import ArgumentParser
from pathlib import Path

parser = ArgumentParser()

parser.add_argument("-c", "--cli", help="Run as CLI", action="store_true")
parser.add_argument("-f", "--folder", help="Folder to process", type=str)
parser.add_argument("-o", "--output", help="Outputs to generate", nargs="+", type=str)
parser.add_argument("--support-kw", help="Minimal support for keywords", type=int)
parser.add_argument("--support-authors", help="Minimal support for authors", type=int)
parser.add_argument("--support-journals", help="Minimal support for journals", type=int)
parser.add_argument("--support-dates", help="Minimal support for dates", type=int)
parser.add_argument("--support", help="Minimal support for all", type=int)
parser.add_argument("--filter-keywords", help="Filter keywords", type=bool, default=False)
parser.add_argument("--filter-lang", help="Filter language", type=bool, default=False)

parser.add_argument("--api", help="Run as API", action="store_true")
parser.add_argument("--host", help="Host to bind to", type=str)
parser.add_argument("--port", help="Port to bind to", type=int)
parser.add_argument(
    "--expose",
    help="Expose the API (shorthand for --host 0.0.0.0 --port 8000), dosent override --host or --port if specified",
    action="store_true",
)


if __name__ == '__main__':
    args = parser.parse_args()

    if args.api or all([args.host, args.port]) or args.expose:
        import uvicorn
        from europarser.api import app

        if args.expose:
            args.host = args.host or "0.0.0.0"

        uvicorn.run(app, host=args.host or "127.0.0.1", port=args.port or 8000)
        exit(0)

    if args.cli:
        if not all([args.folder, args.output]):
            print("You need to specify a input folder and outputs")
            parser.print_help()
            exit(1)

    if not all([args.folder, args.output]):
        parser.print_help()
        exit(1)

    from europarser import main
    from europarser import Params, Output
    from typing import get_args

    possible_outputs = get_args(Output)

    folder = Path(args.folder)
    assert folder.is_dir(), f"Folder {folder} does not exist"
    outputs = args.output
    for output in outputs:
        assert output in possible_outputs, f"Output {output} is not supported"

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
    exit(0)
