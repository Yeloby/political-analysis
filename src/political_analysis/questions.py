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
        r"\b(?:siden|fra)\s+(\d{4})\b",
        text,
        flags=re.IGNORECASE,
    )
    since = int(year_match.group(1)) if year_match else None

    cleaned = re.sub(
        r"\b(?:siden|fra)\s+\d{4}\b",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .?")

    compare_patterns = [
        r"^sammenlign\s+(?:befolkningen\s+i\s+)?"
        r"(.+?)\s+og\s+(.+)$",
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
        r"^vis\s+(?:befolkningen|befolkning)"
        r"(?:sutviklingen)?\s+i\s+(.+)$",
        r"^hvordan\s+har\s+(?:befolkningen|befolkning)"
        r"(?:sutviklingen)?\s+i\s+(.+?)\s+utviklet\s+seg$",
        r"^(?:befolkningen|befolkning)"
        r"(?:sutviklingen)?\s+i\s+(.+)$",
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
class ElectionQuestion:
    party_code: str
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
    key = key.removesuffix("s")

    if key in PARTY_ALIASES:
        return PARTY_ALIASES[key]

    raise ValueError(f"Ukjent parti «{value}».")


def parse_election_question(text: str) -> ElectionQuestion:
    text = " ".join(text.strip().split())

    match = re.search(
        r"^vis\s+(.+?)\s+stortingsvalgresultater\s+i\s+(.+?)"
        r"(?:\s+siden\s+(\d{4}))?[?.]?$",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        raise ValueError(
            "Jeg forstår foreløpig valgspørsmål som "
            "«Vis FrPs stortingsvalgresultater i Trondheim siden 2009»."
        )

    return ElectionQuestion(
        party_code=normalize_party(match.group(1)),
        municipality=match.group(2).strip(),
        since=int(match.group(3)) if match.group(3) else None,
    )


def parse_question(text: str):
    parsers = [
        parse_population_question,
        parse_election_question,
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
