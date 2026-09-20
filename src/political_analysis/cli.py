import argparse

from .analysis import filter_since, summarize_series
from .charts import population_chart
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
    population.add_argument(
        "--chart",
        action="store_true",
        help="Lagre utviklingen som PNG-graf",
    )

    compare = sub.add_parser(
        "compare",
        help="Sammenlign befolkningsutvikling mellom kommuner",
    )
    compare.add_argument(
        "places",
        nargs="+",
        help="Kommuner som skal sammenlignes",
    )
    compare.add_argument(
        "--since",
        type=int,
        help="Sammenlign fra dette året",
    )
    compare.add_argument(
        "--chart",
        action="store_true",
        help="Lagre sammenligningen som PNG-graf",
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

        frame = filter_since(frame, args.since)

        if frame.empty:
            parser.error(
                f"Ingen befolkningsdata fra {args.since}."
            )

        summary = summarize_series(frame)

        first_value = summary.first_value
        last_value = summary.last_value
        change = summary.change
        percent_change = summary.percent_change
        first_year = summary.first_year
        last_year = summary.last_year

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

        if args.chart:
            slug = args.place.casefold().replace(" ", "-")
            output = (
                f"population-{slug}-"
                f"{first_year}-{last_year}.png"
            )
            population_chart(
                [(municipality.name, frame)],
                output,
                f"Befolkningsutvikling i {municipality.name}",
            )
            print(f"Graf: {output}")

        print()

        return 0

    if args.command == "compare":
        if len(args.places) < 2:
            parser.error("Oppgi minst to kommuner som skal sammenlignes.")

        results = []
        chart_series = []

        for place in args.places:
            try:
                municipality, frame = municipality_population(place)
            except ValueError as error:
                parser.error(str(error))

            frame = filter_since(frame, args.since)

            if frame.empty:
                parser.error(
                    f"Ingen befolkningsdata for {municipality.name} "
                    f"fra {args.since}."
                )

            summary = summarize_series(frame)

            first_value = summary.first_value
            last_value = summary.last_value
            change = summary.change
            percent_change = summary.percent_change
            first_year = summary.first_year
            last_year = summary.last_year

            chart_series.append(
                (municipality.name, frame)
            )

            results.append(
                (
                    municipality,
                    first_year,
                    last_year,
                    first_value,
                    last_value,
                    change,
                    percent_change,
                )
            )

        periods = {
            (result[1], result[2])
            for result in results
        }

        print()

        if len(periods) == 1:
            first_year, last_year = next(iter(periods))
            print(f"Sammenligning {first_year}–{last_year}")
        else:
            print("Sammenligning")

        print("=" * 35)

        for (
            municipality,
            first_year,
            last_year,
            first_value,
            last_value,
            change,
            percent_change,
        ) in results:
            first_text = f"{first_value:,}".replace(",", " ")
            last_text = f"{last_value:,}".replace(",", " ")
            change_text = f"{change:+,}".replace(",", " ")
            percent_text = (
                f"{percent_change:+.1f}".replace(".", ",")
            )

            print()
            print(municipality.name)
            print(
                f"{first_text} → {last_text} "
                f"({first_year}–{last_year})"
            )
            print(
                f"Endring: {change_text} personer "
                f"({percent_text} %)"
            )

        print()
        print("Kilde: Statistisk sentralbyrå")
        print("Tabell: 07459")
        print(
            "Metode: SSBs aggregerte kommuneserier "
            "for sammenhengende historiske tall."
        )

        if args.chart:
            years = {
                (result[1], result[2])
                for result in results
            }

            if len(years) == 1:
                chart_first, chart_last = next(iter(years))
                output = (
                    f"population-comparison-"
                    f"{chart_first}-{chart_last}.png"
                )
            else:
                output = "population-comparison.png"

            population_chart(
                chart_series,
                output,
                "Befolkningsutvikling",
            )
            print(f"Graf: {output}")

        print()

        return 0

    return 1
