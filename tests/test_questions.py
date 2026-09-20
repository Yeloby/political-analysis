import pytest

from political_analysis.questions import (
    parse_population_question,
)


def test_single_population_question():
    question = parse_population_question(
        "Vis befolkningen i Trondheim siden 2000"
    )

    assert question.place == "Trondheim"
    assert question.compare_place is None
    assert question.since == 2000


def test_natural_population_question():
    question = parse_population_question(
        "Hvordan har befolkningen i Bergen "
        "utviklet seg siden 2010?"
    )

    assert question.place == "Bergen"
    assert question.compare_place is None
    assert question.since == 2010


def test_comparison_question():
    question = parse_population_question(
        "Sammenlign befolkningen i Trondheim "
        "og Bergen siden 2000"
    )

    assert question.place == "Trondheim"
    assert question.compare_place == "Bergen"
    assert question.since == 2000


def test_simple_comparison_question():
    question = parse_population_question(
        "Sammenlign Trondheim og Tromsø fra 1990"
    )

    assert question.place == "Trondheim"
    assert question.compare_place == "Tromsø"
    assert question.since == 1990


def test_unknown_question():
    with pytest.raises(ValueError):
        parse_population_question(
            "Hvor mange biler finnes i Norge?"
        )
