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
    population.add_argument(
        "--since",
        type=int,
        help="Vis befolkningsutvikling fra dette året",
    )

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

        if args.since is not None:
            years = frame["Tid_code"].astype(int)
            frame = frame[years >= args.since]

            if frame.empty:
                parser.error(
                    f"Ingen befolkningsdata fra {args.since}."
                )

        first = frame.iloc[0]
        last = frame.iloc[-1]

        first_value = int(first["value"])
        last_value = int(last["value"])
        change = last_value - first_value
        percent_change = (change / first_value) * 100

        first_year = first.get("Tid", first.get("Tid_code", ""))
        last_year = last.get("Tid", last.get("Tid_code", ""))

        print()
        print(
            f"{municipality.name}: "
            f"{first_value:,} → {last_value:,} "
            f"({first_year}–{last_year})"
            .replace(",", " ")
        )
        change_text = f"{change:+,}".replace(",", " ")
        percent_text = f"{percent_change:+.1f}".replace(".", ",")

        print(
            f"Endring: {change_text} personer "
            f"({percent_text} %)"
        )

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
        print(f"Periode: {first_year}–{last_year}")
        print(
            "Metode: SSBs aggregerte kommuneserie "
            "for sammenhengende historiske tall."
        )
        print()

        return 0

    return 1
