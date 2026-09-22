import pytest

from samfunnsdata.concepts import normalize_norwegian_text
from samfunnsdata.query_plan import plan_from_population_question, validate_query_plan
from samfunnsdata.questions import (
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


def test_normalization_preserves_norwegian_letters_and_spacing():
    normalized = normalize_norwegian_text("  Folketallet   i  Trondheim  æøå!  ")
    assert normalized == "Folketallet i Trondheim æøå!"


def test_population_synonyms_resolve_equivalently():
    variants = [
        "Befolkningen i Trondheim i 2024",
        "Folketallet i Trondheim i 2024",
        "Hvor mange innbyggere hadde Trondheim i 2024?",
        "Antall innbyggere i Trondheim i 2024",
    ]

    parsed = [parse_population_question(value) for value in variants]
    for question in parsed[1:]:
        assert question.place == parsed[0].place
        assert question.compare_place is None
        assert question.since == parsed[0].since


def test_population_language_planning_is_zero_network(monkeypatch):
    def fail_network(*args, **kwargs):
        raise AssertionError("network.request() was called during language parsing")

    monkeypatch.setattr("samfunnsdata.network.request", fail_network)

    question = parse_population_question("Folketallet i Trondheim i 2024")
    plan = plan_from_population_question(question)
    validate_query_plan(plan)

    assert plan.dataset_id == "ssb-07459-population"
    assert plan.filters["municipality"] == "5001"
    assert plan.filters["year"] == 2024


def test_unknown_question():
    with pytest.raises(ValueError):
        parse_population_question(
            "Hvor mange biler finnes i Norge?"
        )


from samfunnsdata.questions import (
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


from samfunnsdata.questions import (
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
    from samfunnsdata.questions import (
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
    from samfunnsdata.questions import (
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
    from samfunnsdata.questions import (
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

def test_municipal_election_question():
    from samfunnsdata.questions import (
        MunicipalElectionQuestion,
        parse_municipal_election_question,
    )

    question = parse_municipal_election_question(
        "Vis Høyres kommunevalgresultater i Trondheim siden 2011"
    )

    assert isinstance(question, MunicipalElectionQuestion)
    assert question.party_code == "H"
    assert question.municipality == "Trondheim"
    assert question.since == 2011


def test_parse_question_routes_municipal_election():
    from samfunnsdata.questions import (
        MunicipalElectionQuestion,
        parse_question,
    )

    question = parse_question(
        "Vis FrPs kommunevalgresultater i Trondheim siden 2011"
    )

    assert isinstance(question, MunicipalElectionQuestion)
    assert question.party_code == "FRP"
    assert question.municipality == "Trondheim"
    assert question.since == 2011


def test_municipal_election_comparison_question():
    from samfunnsdata.questions import (
        parse_municipal_election_comparison_question,
    )

    question = parse_municipal_election_comparison_question(
        "Sammenlign Høyre og FrP i kommunevalg "
        "i Trondheim siden 2011"
    )

    assert question.first_party_code == "H"
    assert question.second_party_code == "FRP"
    assert question.municipality == "Trondheim"
    assert question.since == 2011


def test_parse_question_routes_municipal_election_comparison():
    from samfunnsdata.questions import (
        MunicipalElectionComparisonQuestion,
        parse_question,
    )

    question = parse_question(
        "Sammenlign Høyre og FrP i kommunevalg "
        "i Trondheim siden 2011"
    )

    assert isinstance(
        question,
        MunicipalElectionComparisonQuestion,
    )
    assert question.first_party_code == "H"
    assert question.second_party_code == "FRP"
    assert question.municipality == "Trondheim"
    assert question.since == 2011


def test_unemployment_question():
    from samfunnsdata.questions import (
        UnemploymentQuestion,
        parse_unemployment_question,
    )

    question = parse_unemployment_question(
        "Hvordan har arbeidsledigheten i Trondheim "
        "utviklet seg siden 2015?"
    )

    assert isinstance(question, UnemploymentQuestion)
    assert question.municipality == "Trondheim"
    assert question.since == 2015


def test_parse_question_routes_unemployment():
    from samfunnsdata.questions import (
        UnemploymentQuestion,
        parse_question,
    )

    question = parse_question(
        "Hvordan har arbeidsledigheten i Trondheim "
        "utviklet seg siden 2015?"
    )

    assert isinstance(question, UnemploymentQuestion)
    assert question.municipality == "Trondheim"
    assert question.since == 2015
