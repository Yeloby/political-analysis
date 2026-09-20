import argparse

from .providers.norway.ssb import SsbClient, municipality_population


def main():
    parser = argparse.ArgumentParser(
        prog="political-analysis",
        description="Analyse norske offentlige data",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    search = sub.add_parser(
        "search",
        help="Søk etter SSB-tabeller",
    )
    search.add_argument("query")

    population = sub.add_parser(
        "population",
        help="Vis befolkningsutvikling",
    )
    population.add_argument("place")

    args = parser.parse_args()

    if args.command == "search":
        client = SsbClient()

        for table in client.search(args.query):
            print(f"{table.id}\t{table.title}")

        return 0

    if args.command == "population":
        try:
            municipality, frame = municipality_population(args.place)
        except ValueError as error:
            parser.error(str(error))

        print()
        print(f"Befolkningsutvikling i {municipality.name}")
        print("=" * 35)

        for _, row in frame.iterrows():
            year = row.get("Tid", row.get("Tid_code", ""))
            value = row["value"]

            if value is not None:
                print(f"{year}: {int(value):,}".replace(",", " "))

        print()
        print("Kilde: Statistisk sentralbyrå")
        print("Tabell: 07459")
        print(f"Kommune: {municipality.name} ({municipality.code})")
        print(
            "Metode: SSBs aggregerte kommuneserie "
            "for sammenhengende historiske tall."
        )
        print()

        return 0

    return 1
