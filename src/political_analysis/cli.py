import argparse

from .providers.norway.ssb import SsbClient


def main():
    parser = argparse.ArgumentParser(prog="political-analysis")
    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser("search")
    search.add_argument("query")

    args = parser.parse_args()

    if args.command == "search":
        client = SsbClient()
        for table in client.search(args.query):
            print(f"{table.id}\t{table.title}")

    return 0
