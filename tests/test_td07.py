from pathlib import Path

import pytest

from slrresearch.plan_and_execute import (
    build_llm_planner,
    build_planning_prompt,
    compare_planning_strategies,
    evaluate_plan,
    execute_step,
    observe_step,
    run_classic,
    run_with_replanning,
    validate_plan,
)
from slrresearch.planning_models import PlanCandidate, PlanStep, PlanningAnalysis
from slrresearch.td07_runtime import (
    controlled_planner,
    controlled_replanner,
    load_td06_handoff,
)


ROOT = Path(__file__).parents[1]
EVIDENCE, REQUIRED_RQS = load_td06_handoff(ROOT / "artifacts" / "td06_evidence.json")
OBJECTIVE = "Produire une note pédagogique couvrant RQ1, RQ2 et RQ3."


def direct_plan():
    return controlled_planner("direct", OBJECTIVE, EVIDENCE)

class FakeStructured:
    def __init__(self, schema, owner): self.schema, self.owner = schema, owner
    def invoke(self, prompt):
        self.owner.calls += 1
        if self.schema is PlanningAnalysis:
            return PlanningAnalysis(proposed_order=["RQ3", "RQ1", "RQ2"], rationale=["Comparer avant d'exécuter"], risks=[])
        return PlanCandidate(strategy="direct", objective=OBJECTIVE, steps=[
            {"id":"A","rq_id":"RQ1","objective":"a","evidence_ids":["E1"],"required_facets":["high_recall"]},
            {"id":"B","rq_id":"RQ2","objective":"b","evidence_ids":["E3"],"required_facets":["workload_reduction"]},
            {"id":"C","rq_id":"RQ3","objective":"c","evidence_ids":["E5"],"required_facets":["human_oversight"]},
        ])

class FakeModel:
    def __init__(self): self.calls = 0
    def with_structured_output(self, schema): return FakeStructured(schema, self)

@pytest.mark.parametrize(("strategy", "expected_calls"), [("direct", 1), ("cot", 2), ("tot", 3)])
def test_todo_1_implementations_llm_distinctes(strategy, expected_calls):
    model = FakeModel()
    plan = build_llm_planner(model)(strategy, OBJECTIVE, EVIDENCE)
    assert model.calls == expected_calls
    assert plan.strategy == strategy


def test_todo_1_trois_guidages_distincts_meme_specification():
    prompts = {
        strategy: build_planning_prompt(strategy, OBJECTIVE, EVIDENCE)
        for strategy in ["direct", "cot", "tot"]
    }
    assert all(OBJECTIVE in prompt and "E1" in prompt for prompt in prompts.values())
    assert "directement" in prompts["direct"].lower()
    assert "justifications" in prompts["cot"].lower()
    assert "plusieurs" in prompts["tot"].lower()


def test_todo_2_validation_bloque_preuve_et_dependance_inconnues():
    plan = direct_plan()
    validate_plan(plan, {item.id for item in EVIDENCE}, REQUIRED_RQS)
    bad_evidence = plan.model_copy(deep=True)
    bad_evidence.steps[0].evidence_ids = ["E999"]
    with pytest.raises(ValueError, match="Preuve"):
        validate_plan(bad_evidence, {item.id for item in EVIDENCE}, REQUIRED_RQS)
    bad_dependency = plan.model_copy(deep=True)
    bad_dependency.steps[0].depends_on = ["S999"]
    with pytest.raises(ValueError, match="Dépendance"):
        validate_plan(bad_dependency, {item.id for item in EVIDENCE}, REQUIRED_RQS)


def test_todo_2_validation_refuse_rq_dupliquee_et_auto_dependance():
    plan = direct_plan()
    duplicate_rq = plan.model_copy(deep=True)
    duplicate_rq.steps[1].rq_id = duplicate_rq.steps[0].rq_id
    with pytest.raises(ValueError, match="Question de recherche"):
        validate_plan(duplicate_rq, {item.id for item in EVIDENCE}, REQUIRED_RQS)
    self_dependency = plan.model_copy(deep=True)
    self_dependency.steps[0].depends_on = [self_dependency.steps[0].id]
    with pytest.raises(ValueError, match="elle-même"):
        validate_plan(self_dependency, {item.id for item in EVIDENCE}, REQUIRED_RQS)


def test_todo_3_compare_exactement_direct_cot_tot_sur_memes_entrees():
    calls = []

    def planner(strategy, objective, evidence):
        calls.append((strategy, objective, [item.id for item in evidence]))
        return controlled_planner(strategy, objective, evidence)

    comparison = compare_planning_strategies(planner, OBJECTIVE, EVIDENCE, REQUIRED_RQS)
    assert [item["strategy"] for item in comparison] == ["direct", "cot", "tot"]
    assert len(calls) == 3
    assert len({objective for _, objective, _ in calls}) == 1
    assert len({tuple(ids) for _, _, ids in calls}) == 1


def test_todo_4_execute_controle_permissions_dependances_et_facettes():
    evidence_by_id = {item.id: item for item in EVIDENCE}
    result = execute_step(direct_plan().steps[2], evidence_by_id, {"S1", "S2"})
    assert result.status == "insufficient_evidence"
    assert "human_oversight" in result.covered_facets
    assert "prospective_validation" in result.missing_facets
    blocked = execute_step(direct_plan().steps[2], evidence_by_id, set())
    assert blocked.status == "blocked"


def test_todo_5_classique_retry_sans_modifier_plan_puis_abstient():
    plan = direct_plan()
    before = plan.model_dump()
    result = run_classic(plan, EVIDENCE, REQUIRED_RQS, max_retries=1)
    assert result.status == "abstained"
    assert result.revisions == 0
    assert plan.model_dump() == before
    assert [event.decision for event in result.trace][-2:] == ["retry", "abstain"]


def test_todo_6_replanning_revalide_et_termine_sans_inventer_preuve():
    result = run_with_replanning(
        direct_plan(), EVIDENCE, REQUIRED_RQS, controlled_replanner, max_revisions=1
    )
    assert result.status == "completed"
    assert result.revisions == 1
    assert "replan" in [event.decision for event in result.trace]
    validate_plan(result.plan, {item.id for item in EVIDENCE}, REQUIRED_RQS)
    assert {citation for section in result.sections for citation in section.citations} <= {
        item.paper_id for item in EVIDENCE
    }
