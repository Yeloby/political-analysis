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


from political_analysis.questions import (
    normalize_party,
    parse_election_question,
)


def test_party_alias_frp():
    assert normalize_party("FrP") == "FRP"
    assert normalize_party("FrPs") == "FRP"
    assert normalize_party("Fremskrittspartiet") == "FRP"


def test_election_question():
    question = parse_election_question(
        "Vis FrPs stortingsvalgresultater i Trondheim siden 2009"
    )

    assert question.party_code == "FRP"
    assert question.municipality == "Trondheim"
    assert question.since == 2009


from political_analysis.questions import (
    ElectionQuestion,
    PopulationQuestion,
    parse_question,
)


def test_parse_question_routes_population():
    question = parse_question(
        "Vis befolkningen i Trondheim siden 2000"
    )

    assert isinstance(question, PopulationQuestion)


def test_parse_question_routes_election():
    question = parse_question(
        "Vis FrPs stortingsvalgresultater i Trondheim siden 2009"
    )

    assert isinstance(question, ElectionQuestion)
    assert question.party_code == "FRP"
    assert question.municipality == "Trondheim"
    assert question.since == 2009


def test_natural_election_question():
    question = parse_election_question(
        "Hvordan har FrP gjort det i stortingsvalg "
        "i Trondheim siden 2009?"
    )

    assert question.party_code == "FRP"
    assert question.municipality == "Trondheim"
    assert question.since == 2009


def test_election_development_question():
    question = parse_election_question(
        "Hvordan har Høyre utviklet seg i stortingsvalg "
        "i Bergen fra 2013?"
    )

    assert question.party_code == "H"
    assert question.municipality == "Bergen"
    assert question.since == 2013


def test_short_election_question():
    question = parse_election_question(
        "Vis Arbeiderpartiet i stortingsvalget i Oslo"
    )

    assert question.party_code == "A"
    assert question.municipality == "Oslo"
    assert question.since is None


def test_election_comparison_question():
    from political_analysis.questions import (
        ElectionComparisonQuestion,
        parse_election_comparison_question,
    )

    question = parse_election_comparison_question(
        "Sammenlign FrP og Høyre i stortingsvalg "
        "i Trondheim siden 2009"
    )

    assert isinstance(
        question,
        ElectionComparisonQuestion,
    )
    assert question.first_party_code == "FRP"
    assert question.second_party_code == "H"
    assert question.municipality == "Trondheim"
    assert question.since == 2009


def test_election_comparison_with_med():
    from political_analysis.questions import (
        parse_election_comparison_question,
    )

    question = parse_election_comparison_question(
        "Sammenlign Arbeiderpartiet med SV "
        "i stortingsvalget i Oslo fra 2013"
    )

    assert question.first_party_code == "A"
    assert question.second_party_code == "SV"
    assert question.municipality == "Oslo"
    assert question.since == 2013


def test_router_prefers_election_comparison():
    from political_analysis.questions import (
        ElectionComparisonQuestion,
        parse_question,
    )

    question = parse_question(
        "Sammenlign FrP og Høyre i stortingsvalg "
        "i Trondheim siden 2009"
    )

    assert isinstance(
        question,
        ElectionComparisonQuestion,
    )
    assert question.first_party_code == "FRP"
    assert question.second_party_code == "H"
    assert question.municipality == "Trondheim"
    assert question.since == 2009
