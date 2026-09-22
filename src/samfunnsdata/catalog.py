from dataclasses import dataclass
from enum import StrEnum


class SupportStatus(StrEnum):
    SUPPORTED = "supported"
    DISCOVERED = "discovered"
    PLANNED = "planned"


@dataclass(frozen=True)
class Source:
    id: str
    authority: str
    url: str


SOURCES = (
    Source("ssb", "Statistisk sentralbyrå", "https://www.ssb.no"),
    Source("fhi", "Folkehelseinstituttet", "https://www.fhi.no"),
    Source("nav", "NAV", "https://www.nav.no"),
    Source("elections", "Valgdirektoratet", "https://valgresultat.no"),
)


def get_source(provider: str) -> Source:
    for source in SOURCES:
        if source.id == provider:
            return source
    raise KeyError(f"Ukjent datakilde: {provider}")


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
    support: SupportStatus = SupportStatus.PLANNED
    adapter: str | None = None
    interfaces: tuple[str, ...] = ()
    table_id: str | None = None
    source_url: str | None = None
    access_url: str | None = None
    format: str | None = None
    updated_at: str | None = None
    methodology: tuple[str, ...] = ()
    series_breaks: tuple[str, ...] = ()
    official_statistics: bool | None = None

    def __post_init__(self):
        if not isinstance(self.support, SupportStatus):
            raise TypeError("support må være en SupportStatus.")
        if self.support == SupportStatus.SUPPORTED:
            if not self.adapter or not self.interfaces:
                raise ValueError("Støttede datasett må angi adapter og grensesnitt.")
        elif self.adapter or self.interfaces:
            raise ValueError("Katalogiserte/planlagte datasett kan ikke angi kjørbar støtte.")

    @property
    def queryable(self) -> bool:
        """Dataset-level support; this does not imply GUI or arbitrary query support."""
        return self.support == SupportStatus.SUPPORTED

    @property
    def support_label(self) -> str:
        if self.support == SupportStatus.SUPPORTED:
            channels = {"python": "Python/API", "gui": "GUI", "cli": "CLI"}
            return "Støttet: " + ", ".join(channels.get(x, x) for x in self.interfaces)
        if self.support == SupportStatus.DISCOVERED:
            return "Katalogisert – kan ikke hentes i Samfunnsdata"
        return "Planlagt – ikke støttet"


DATASETS = (
    Dataset(
        id="fhi-lmr-825-medicines",
        support=SupportStatus.SUPPORTED,
        adapter="samfunnsdata.providers.norway.medicines:medicine_history",
        interfaces=("python",),
        table_id="lmr/825",
        source_url="https://statistikk-data.fhi.no/api/open/v1/lmr/table/825/metadata",
        access_url="https://statistikk-data.fhi.no/api/open/v1/lmr/Table/825/data",
        format="json-stat2",
        provider="fhi",
        title="Legemidler etter ATC-kode",
        topic="health / medicines",
        source="FHI Legemiddelregisteret (lmr), tabell 825",
        geography=(),
        time_resolution="year",
        dimensions=("atc", "sex", "age", "year", "measure"),
        unit="measure_dependent",
        description="Legemiddelstatistikk etter ATC-kode, kjønn, alder og år.",
        period="2004– (tilgjengelige år hentes fra FHI)",
        measures=("users", "users_per_1000", "ddd", "population"),
        definition="FHI-tabellen «Per ATC-kode», med måltall levert av FHI.",
        limitations=(
            "Brukertall skal ikke summeres på tvers av ATC-koder.",
            "Manglende og skjulte observasjoner må beholde status.",
            "Enhet avhenger av valgt måltall.",
        ),
        aliases=("legemidler", "legemiddel", "medisiner", "ATC"),
    ),
    Dataset(
        id="ssb-07459-population",
        support=SupportStatus.SUPPORTED,
        adapter="samfunnsdata.providers.norway.ssb:municipality_population",
        interfaces=("python", "gui", "cli"),
        table_id="07459",
        source_url="https://www.ssb.no/statbank/table/07459",
        access_url="https://data.ssb.no/api/pxwebapi/v2/tables/07459/data",
        format="json-stat2",
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
        id="valg-parliament-results",
        support=SupportStatus.SUPPORTED,
        adapter="samfunnsdata.providers.norway.elections:storting_party_history",
        interfaces=("python", "gui"),
        source_url="https://valgresultat.no",
        access_url="https://valgresultat.no/api",
        format="json",
        provider="elections",
        title="Stortingsvalg",
        topic="elections",
        source="Valgdirektoratet",
        geography=("municipality",),
        time_resolution="election",
        dimensions=("geography", "year", "party"),
        unit="votes_percent",
        description=(
            "Partienes resultater ved norske stortingsvalg."
        ),
        period="2009–2025 (implementerte årganger)",
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
        aliases=("stortingsvalg", "stortingsvalgresultat"),
    ),
    Dataset(
        id="valg-municipality-results",
        support=SupportStatus.SUPPORTED,
        adapter="samfunnsdata.providers.norway.elections:municipality_party_history",
        interfaces=("python", "gui"),
        source_url="https://valgresultat.no",
        access_url="https://valgresultat.no/api",
        format="json",
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
        support=SupportStatus.SUPPORTED,
        adapter="samfunnsdata.providers.norway.nav:municipality_unemployment_since",
        interfaces=("python", "gui"),
        source_url="https://www.nav.no",
        format="csv",
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


def find_datasets(
    query: str,
    *,
    provider: str | None = None,
    support: SupportStatus | None = None,
) -> list[Dataset]:
    candidates = [
        item for item in DATASETS
        if (provider is None or item.provider == provider)
        and (support is None or item.support == support)
    ]
    words = set()

    for raw_word in query.casefold().split():
        word = raw_word.strip(" ,.?!:;()")

        if len(word) >= 3:
            words.update(_search_forms(word))

    if not words:
        return candidates

    scored = []

    for dataset in candidates:
        searchable = " ".join(
            [
                dataset.title,
                dataset.topic,
                dataset.description,
                dataset.provider,
                dataset.source,
                get_source(dataset.provider).authority,
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
