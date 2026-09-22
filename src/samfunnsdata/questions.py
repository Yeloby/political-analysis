import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PopulationQuestion:
    place: str
    compare_place: str | None = None
    since: int | None = None


def parse_population_question(text: str) -> PopulationQuestion:
    text = " ".join(text.strip().split())

    if not text:
        raise ValueError("Skriv inn et spørsmål.")

    year_match = re.search(
        r"\b(?:siden|fra|i)\s+(\d{4})\b",
        text,
        flags=re.IGNORECASE,
    )
    since = int(year_match.group(1)) if year_match else None

    cleaned = re.sub(
        r"\b(?:siden|fra|i)\s+\d{4}\b",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .?")

    compare_patterns = [
        (
            r"^sammenlign\s+(?:befolkningen\s+i\s+)?"
            r"(.+?)\s+og\s+(.+)$"
        ),
        r"^sammenlign\s+(.+?)\s+med\s+(.+)$",
    ]

    for pattern in compare_patterns:
        match = re.search(
            pattern,
            cleaned,
            flags=re.IGNORECASE,
        )
        if match:
            return PopulationQuestion(
                place=_clean_place(match.group(1)),
                compare_place=_clean_place(match.group(2)),
                since=since,
            )

    single_patterns = [
        (
            r"^vis\s+(?:befolkningen|befolkning)"
            r"(?:sutviklingen)?\s+i\s+(.+)$"
        ),
        (
            r"^hvordan\s+har\s+(?:befolkningen|befolkning)"
            r"(?:sutviklingen)?\s+i\s+(.+?)\s+utviklet\s+seg$"
        ),
        (
            r"^(?:befolkningen|befolkning)"
            r"(?:sutviklingen)?\s+i\s+(.+)$"
        ),
    ]

    for pattern in single_patterns:
        match = re.search(
            pattern,
            cleaned,
            flags=re.IGNORECASE,
        )
        if match:
            return PopulationQuestion(
                place=_clean_place(match.group(1)),
                since=since,
            )

    raise ValueError(
        "Jeg forstår foreløpig befolkningsspørsmål som "
        "«Vis befolkningen i Trondheim siden 2000» eller "
        "«Sammenlign Trondheim og Bergen siden 2000»."
    )


def _clean_place(value: str) -> str:
    value = value.strip(" ,.?")
    value = re.sub(
        r"^(?:befolkningen|befolkning)\s+i\s+",
        "",
        value,
        flags=re.IGNORECASE,
    )
    return value.strip()



@dataclass(frozen=True)
class UnemploymentQuestion:
    municipality: str
    since: int | None = None


def parse_unemployment_question(
    text: str,
) -> UnemploymentQuestion:
    text = " ".join(text.strip().split())

    year_match = re.search(
        r"\b(?:siden|fra)\s+(\d{4})\b",
        text,
        flags=re.IGNORECASE,
    )
    since = int(year_match.group(1)) if year_match else None

    cleaned = re.sub(
        r"\s+(?:siden|fra)\s+\d{4}\b",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .?")

    patterns = [
        (
            r"^hvordan\s+har\s+arbeidsledigheten\s+i\s+"
            r"(.+?)\s+utviklet\s+seg$"
        ),
        (
            r"^vis\s+arbeidsledigheten\s+i\s+(.+)$"
        ),
        (
            r"^arbeidsledigheten\s+i\s+(.+)$"
        ),
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            cleaned,
            flags=re.IGNORECASE,
        )

        if match:
            return UnemploymentQuestion(
                municipality=match.group(1).strip(" ,.?!"),
                since=since,
            )

    raise ValueError(
        "Jeg forstår foreløpig arbeidsledighetsspørsmål som "
        "«Hvordan har arbeidsledigheten i Trondheim "
        "utviklet seg siden 2015?»."
    )

@dataclass(frozen=True)
class ElectionQuestion:
    party_code: str
    municipality: str
    since: int | None = None


@dataclass(frozen=True)
class MunicipalElectionQuestion:
    party_code: str
    municipality: str
    since: int | None = None


@dataclass(frozen=True)
class MunicipalElectionComparisonQuestion:
    first_party_code: str
    second_party_code: str
    municipality: str
    since: int | None = None


@dataclass(frozen=True)
class ElectionComparisonQuestion:
    first_party_code: str
    second_party_code: str
    municipality: str
    since: int | None = None


PARTY_ALIASES = {
    "ap": "A",
    "arbeiderpartiet": "A",
    "frp": "FRP",
    "fremskrittspartiet": "FRP",
    "høyre": "H",
    "h": "H",
    "sv": "SV",
    "sosialistisk venstreparti": "SV",
    "sp": "SP",
    "senterpartiet": "SP",
    "krf": "KRF",
    "kristelig folkeparti": "KRF",
    "venstre": "V",
    "v": "V",
    "mdg": "MDG",
    "miljøpartiet de grønne": "MDG",
    "rødt": "RØDT",
}


def normalize_party(value: str) -> str:
    key = value.casefold().strip()

    if key in PARTY_ALIASES:
        return PARTY_ALIASES[key]

    if key.endswith("s") and key[:-1] in PARTY_ALIASES:
        return PARTY_ALIASES[key[:-1]]

    raise ValueError(f"Ukjent parti «{value}».")


def parse_election_comparison_question(
    text: str,
) -> ElectionComparisonQuestion:
    text = " ".join(text.strip().split())

    year_match = re.search(
        r"\b(?:siden|fra)\s+(\d{4})\b",
        text,
        flags=re.IGNORECASE,
    )
    since = int(year_match.group(1)) if year_match else None

    cleaned = re.sub(
        r"\s+(?:siden|fra)\s+\d{4}\b",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .?")

    patterns = [
        (
            r"^sammenlign\s+(.+?)\s+og\s+(.+?)\s+"
            r"i\s+stortingsvalg(?:et)?\s+i\s+(.+)$"
        ),
        (
            r"^sammenlign\s+(.+?)\s+med\s+(.+?)\s+"
            r"i\s+stortingsvalg(?:et)?\s+i\s+(.+)$"
        ),
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            cleaned,
            flags=re.IGNORECASE,
        )

        if match:
            return ElectionComparisonQuestion(
                first_party_code=normalize_party(
                    match.group(1)
                ),
                second_party_code=normalize_party(
                    match.group(2)
                ),
                municipality=match.group(3).strip(" ,.?!"),
                since=since,
            )

    raise ValueError(
        "Jeg forstår foreløpig partisammenligninger som "
        "«Sammenlign FrP og Høyre i stortingsvalg "
        "i Trondheim siden 2009»."
    )


def parse_municipal_election_comparison_question(
    text: str,
) -> MunicipalElectionComparisonQuestion:
    text = " ".join(text.strip().split())

    year_match = re.search(
        r"\b(?:siden|fra)\s+(\d{4})\b",
        text,
        flags=re.IGNORECASE,
    )
    since = int(year_match.group(1)) if year_match else None

    cleaned = re.sub(
        r"\s+(?:siden|fra)\s+\d{4}\b",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .?")

    patterns = [
        (
            r"^sammenlign\s+(.+?)\s+og\s+(.+?)\s+"
            r"i\s+kommunevalg(?:et)?\s+i\s+(.+)$"
        ),
        (
            r"^sammenlign\s+(.+?)\s+med\s+(.+?)\s+"
            r"i\s+kommunevalg(?:et)?\s+i\s+(.+)$"
        ),
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            cleaned,
            flags=re.IGNORECASE,
        )

        if match:
            return MunicipalElectionComparisonQuestion(
                first_party_code=normalize_party(match.group(1)),
                second_party_code=normalize_party(match.group(2)),
                municipality=match.group(3).strip(" ,.?!"),
                since=since,
            )

    raise ValueError(
        "Jeg forstår foreløpig kommunevalgsammenligninger som "
        "«Sammenlign Høyre og FrP i kommunevalg "
        "i Trondheim siden 2011»."
    )


def parse_municipal_election_question(
    text: str,
) -> MunicipalElectionQuestion:
    text = " ".join(text.strip().split())

    year_match = re.search(
        r"\b(?:siden|fra)\s+(\d{4})\b",
        text,
        flags=re.IGNORECASE,
    )
    since = int(year_match.group(1)) if year_match else None

    cleaned = re.sub(
        r"\s+(?:siden|fra)\s+\d{4}\b",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .?")

    match = re.fullmatch(
        r"vis\s+(.+?)\s+kommunevalgresultater\s+i\s+(.+)",
        cleaned,
        flags=re.IGNORECASE,
    )

    if not match:
        raise ValueError(
            "Ugyldig kommunevalgspørsmål."
        )

    party = normalize_party(match.group(1))
    municipality = match.group(2).strip()

    return MunicipalElectionQuestion(
        party_code=party,
        municipality=municipality,
        since=since,
    )


def parse_election_question(text: str) -> ElectionQuestion:
    text = " ".join(text.strip().split())

    year_match = re.search(
        r"\b(?:siden|fra)\s+(\d{4})\b",
        text,
        flags=re.IGNORECASE,
    )
    since = int(year_match.group(1)) if year_match else None

    cleaned = re.sub(
        r"\s+(?:siden|fra)\s+\d{4}\b",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .?")

    patterns = [
        (
            r"^vis\s+(.+?)\s+"
            r"stortingsvalgresultater\s+i\s+(.+)$"
        ),
        (
            r"^hvordan\s+har\s+(.+?)\s+gjort\s+det\s+"
            r"i\s+stortingsvalg(?:et)?\s+i\s+(.+)$"
        ),
        (
            r"^hvordan\s+har\s+(.+?)\s+utviklet\s+seg\s+"
            r"i\s+stortingsvalg(?:et)?\s+i\s+(.+)$"
        ),
        (
            r"^vis\s+(.+?)\s+i\s+stortingsvalg(?:et)?\s+"
            r"i\s+(.+)$"
        ),
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            cleaned,
            flags=re.IGNORECASE,
        )

        if match:
            return ElectionQuestion(
                party_code=normalize_party(match.group(1)),
                municipality=match.group(2).strip(" ,.?!"),
                since=since,
            )

    raise ValueError(
        "Jeg forstår foreløpig valgspørsmål som "
        "«Vis FrPs stortingsvalgresultater i Trondheim siden 2009» "
        "eller «Hvordan har FrP gjort det i stortingsvalg i "
        "Trondheim siden 2009?»."
    )


def parse_question(text: str):
    parsers = [
        parse_unemployment_question,
        parse_election_comparison_question,
        parse_municipal_election_comparison_question,
        parse_municipal_election_question,
        parse_election_question,
        parse_population_question,
    ]

    errors = []

    for parser in parsers:
        try:
            return parser(text)
        except ValueError as error:
            errors.append(str(error))

    raise ValueError(
        "Jeg forstår ikke spørsmålet ennå. "
        "Prøv for eksempel «Vis befolkningen i Trondheim siden 2000» "
        "eller «Vis FrPs stortingsvalgresultater i Trondheim siden 2009»."
    )
