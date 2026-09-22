import json

import pytest

from samfunnsdata.catalog import SupportStatus, get_dataset
from samfunnsdata.population import parse_population_question
from samfunnsdata.query_plan import (
    QueryPlan,
    QueryPlanValidationError,
    execute_query_plan,
    plan_from_population_question,
    validate_query_plan,
)


def test_query_plan_round_trip_and_hash():
    plan = QueryPlan(
        dataset_id="ssb-07459-population",
        operation="lookup",
        filters={"municipality": "5001", "year": 2024},
        measure="population",
        grouping=(),
        ordering=(),
        limit=None,
    )
    encoded = plan.to_json()
    loaded = QueryPlan.from_json(encoded)
    assert loaded == plan
    assert plan.canonical_json() == loaded.canonical_json()
    assert len(plan.plan_hash()) == 64
    assert plan.plan_hash() == loaded.plan_hash()


def test_query_plan_rejects_unsupported_schema_version():
    with pytest.raises(QueryPlanValidationError, match="schema"):
        validate_query_plan({"schema_version": 99, "dataset_id": "ssb-07459-population", "operation": "lookup", "filters": {}, "measure": "population"})


def test_query_plan_rejects_unknown_dataset():
    with pytest.raises(QueryPlanValidationError, match="dataset"):
        validate_query_plan({"schema_version": 1, "dataset_id": "missing-dataset", "operation": "lookup", "filters": {"municipality": "5001"}, "measure": "population"})


def test_query_plan_rejects_discovered_dataset():
    dataset = get_dataset("ssb-07459-population")
    assert dataset.support == SupportStatus.SUPPORTED
    discovered = {**dataset.__dict__, "support": SupportStatus.DISCOVERED}
    with pytest.raises(QueryPlanValidationError, match="SUPPORTED|supported"):
        validate_query_plan({"schema_version": 1, "dataset_id": "ssb-07459-population", "operation": "lookup", "filters": {"municipality": "5001", "year": 2024}, "measure": "population"}, dataset_override=discovered)


def test_population_question_creates_expected_plan():
    question = parse_population_question("Vis befolkningen i Trondheim i 2024")
    plan = plan_from_population_question(question)
    assert plan.dataset_id == "ssb-07459-population"
    assert plan.operation == "lookup"
    assert plan.measure == "population"
    assert plan.filters["municipality"] == "5001"
    assert plan.filters["year"] == 2024


def test_query_plan_rejects_unknown_measure_and_filter_dimension():
    with pytest.raises(QueryPlanValidationError, match="measure"):
        validate_query_plan({"schema_version": 1, "dataset_id": "ssb-07459-population", "operation": "lookup", "filters": {"municipality": "5001", "year": 2024}, "measure": "not-real"})

    with pytest.raises(QueryPlanValidationError, match="filter|dimension"):
        validate_query_plan({"schema_version": 1, "dataset_id": "ssb-07459-population", "operation": "lookup", "filters": {"alien": "value", "year": 2024}, "measure": "population"})


def test_query_plan_rejects_missing_required_population_selection():
    with pytest.raises(QueryPlanValidationError, match="municipality"):
        validate_query_plan({"schema_version": 1, "dataset_id": "ssb-07459-population", "operation": "lookup", "filters": {"year": 2024}, "measure": "population"})


def test_query_plan_rejects_invalid_year_type():
    with pytest.raises(QueryPlanValidationError, match="year|integer"):
        validate_query_plan({"schema_version": 1, "dataset_id": "ssb-07459-population", "operation": "lookup", "filters": {"municipality": "5001", "year": "not-a-year"}, "measure": "population"})


def test_execute_query_plan_uses_local_mapping_and_produces_result():
    plan = QueryPlan(
        dataset_id="ssb-07459-population",
        operation="lookup",
        filters={"municipality": "5001", "year": 2025},
        measure="population",
    )
    result = execute_query_plan(plan)
    assert result.title
    assert result.receipt.schema_version in {"1", "2"}
    assert result.receipt.query_plan_hash == plan.plan_hash()
    assert "question" not in json.dumps(result.receipt.to_dict()).lower()
