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
