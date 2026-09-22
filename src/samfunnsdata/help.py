"""Packaged, offline user documentation shared by desktop views and tests."""

import json
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from importlib.resources import files

from . import __version__

ATTRIBUTION = "Laget av Johan Slåttavik"
TAGLINE = "Offentlige data. Etterprøvbare svar."
DESCRIPTION = (
    "Samfunnsdata er et gratis og åpent program for utforskning "
    "og analyse av norske offentlige data."
)


@dataclass(frozen=True)
class HelpSection:
    id: str
    title: str
    text: str


def help_sections() -> tuple[HelpSection, ...]:
    content = files("samfunnsdata").joinpath("help_content.json").read_text(encoding="utf-8")
    return tuple(HelpSection(**item) for item in json.loads(content))


def application_version() -> str:
    try:
        return version("samfunnsdata")
    except PackageNotFoundError:
        return __version__
