from dataclasses import dataclass


@dataclass(frozen=True)
class Dataset:
    id: str
    provider: str
    title: str
    topic: str
    source: str
    geography: tuple[str, ...]
    time_resolution: str
    dimensions: tuple[str, ...]
    unit: str
    description: str
    period: str
    measures: tuple[str, ...]
    definition: str
    limitations: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()


DATASETS = (
    Dataset(
        id="ssb-07459-population",
        provider="ssb",
        title="Befolkning",
        topic="demography",
        source="SSB 07459",
        geography=("municipality",),
        time_resolution="year",
        dimensions=("geography", "year"),
        unit="persons",
        description=(
            "Folkemengde i norske kommuner over tid."
        ),
        period="1986–",
        measures=("population",),
        definition="Folkemengde etter SSBs kommunestatistikk.",
        aliases=("befolkning", "folketall", "innbyggere"),
    ),
    Dataset(
        id="valg-municipality-results",
        provider="elections",
        title="Kommunevalg",
        topic="elections",
        source="Valgdirektoratet",
        geography=("municipality",),
        time_resolution="election",
        dimensions=("geography", "year", "party"),
        unit="votes_percent",
        description=(
            "Partienes resultater ved norske kommunevalg."
        ),
        period="2011–",
        measures=("votes", "votes_percent"),
        definition=(
            "Offisielle valgresultater etter kommune og parti."
        ),
        limitations=(
            (
                "Historisk dekning avhenger av tilgjengelige "
                "valgdata."
            ),
        ),
        aliases=("kommunevalg", "valgresultat", "valgresultater"),
    ),
    Dataset(
        id="nav-registered-unemployed",
        provider="nav",
        title="Registrerte helt ledige",
        topic="labour",
        source="NAV",
        geography=("municipality",),
        time_resolution="month",
        dimensions=("geography", "year", "month"),
        unit="persons_and_percent",
        description=(
            "NAV-registrerte helt ledige etter kommune og måned."
        ),
        period="1995–2025",
        measures=("unemployed", "percent"),
        definition=(
            "Personer registrert som helt ledige hos NAV."
        ),
        limitations=(
            "Serien kan inneholde brudd i statistikken.",
            "Må ikke forveksles med arbeidsledighet målt i AKU.",
        ),
        aliases=(
            "arbeidsledighet",
            "arbeidsledig",
            "arbeidsledige",
            "ledighet",
            "helt ledige",
        ),
    ),
)


def datasets() -> tuple[Dataset, ...]:
    return DATASETS


def _search_forms(word: str) -> set[str]:
    forms = {word}

    for suffix in ("ene", "en", "et", "a"):
        if word.endswith(suffix) and len(word) > len(suffix) + 3:
            forms.add(word[:-len(suffix)])

    return forms


def find_datasets(query: str) -> list[Dataset]:
    words = set()

    for raw_word in query.casefold().split():
        word = raw_word.strip(" ,.?!:;()")

        if len(word) >= 3:
            words.update(_search_forms(word))

    if not words:
        return list(DATASETS)

    scored = []

    for dataset in DATASETS:
        searchable = " ".join(
            [
                dataset.title,
                dataset.topic,
                dataset.description,
                dataset.provider,
                dataset.source,
                dataset.definition,
                *dataset.dimensions,
                *dataset.measures,
                *dataset.aliases,
            ]
        ).casefold()

        score = sum(
            1
            for word in words
            if word in searchable
        )

        if score:
            scored.append((score, dataset))

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1].title.casefold(),
        )
    )

    return [
        dataset
        for _, dataset in scored
    ]


def get_dataset(dataset_id: str) -> Dataset:
    for dataset in DATASETS:
        if dataset.id == dataset_id:
            return dataset

    raise KeyError(f"Ukjent datasett: {dataset_id}")
