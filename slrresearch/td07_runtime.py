import json
from pathlib import Path

from .planning_models import EvidenceItem, ExecutionResult, PlanCandidate, PlanStep


def load_td06_handoff(path: Path) -> tuple[list[EvidenceItem], set[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    evidence = [EvidenceItem.model_validate(item) for item in payload["evidence"]]
    return evidence, set(payload["required_rqs"])


def controlled_planner(
    strategy: str, objective: str, evidence: list[EvidenceItem]
) -> PlanCandidate:
    """Trois plans comparables, sans dépendre d'un LLM dans les tests."""
    traces = {
        "direct": [],
        "cot": [
            "Organiser les preuves par RQ avant la rédaction.",
            "Faire dépendre la comparaison des synthèses terminées.",
        ],
        "tot": [
            "Piste par RQ : couverture forte et provenance simple.",
            "Piste par thème : comparaison aisée, RQ moins visibles.",
            "Piste par étude : traçabilité forte, synthèse fragmentée.",
            "Retenir la piste par RQ avec discussion transversale.",
        ],
    }
    direct_steps = [
        PlanStep(id="S1", rq_id="RQ1", objective="Comparer les sensibilités observées.", evidence_ids=["E1", "E2"], required_facets=["high_recall", "threshold_tradeoff"]),
        PlanStep(id="S2", rq_id="RQ2", objective="Comparer gain de charge et risque d'erreur.", evidence_ids=["E3", "E4"], required_facets=["workload_reduction", "recall_workload_tradeoff"], depends_on=["S1"]),
        PlanStep(id="S3", rq_id="RQ3", objective="Présenter les mécanismes de contrôle et de validation, y compris la validation prospective.", evidence_ids=["E5", "E6"], required_facets=["human_oversight", "domain_validation", "prospective_validation"], depends_on=["S1", "S2"]),
    ]
    cot_steps = [
        PlanStep(id="C1", rq_id="RQ3", objective="Présenter d'abord les mécanismes de contrôle déjà étayés.", evidence_ids=["E5", "E6"], required_facets=["human_oversight", "domain_validation"]),
        PlanStep(id="C2", rq_id="RQ1", objective="Comparer ensuite les sensibilités.", evidence_ids=["E1", "E2"], required_facets=["high_recall", "threshold_tradeoff"], depends_on=["C1"]),
        PlanStep(id="C3", rq_id="RQ2", objective="Terminer par le compromis opérationnel en rapprochant deux extractions de la même étude et une étude d'ensemble.", evidence_ids=["E2", "E7", "E4"], required_facets=["threshold_tradeoff", "workload_reduction", "recall_workload_tradeoff"], depends_on=["C1", "C2"]),
    ]
    tot_steps = [
        PlanStep(id="T1", rq_id="RQ2", objective="Commencer par le compromis décisionnel.", evidence_ids=["E3", "E4"], required_facets=["workload_reduction", "recall_workload_tradeoff"]),
        PlanStep(id="T2", rq_id="RQ1", objective="Relier ce compromis aux performances.", evidence_ids=["E1", "E2"], required_facets=["high_recall", "threshold_tradeoff"]),
        PlanStep(id="T3", rq_id="RQ3", objective="Conclure par les mécanismes de contrôle disponibles et leurs limites de domaine.", evidence_ids=["E5", "E6", "E8"], required_facets=["human_oversight", "domain_validation", "prompt_calibration"], depends_on=["T1", "T2"]),
    ]
    plans = {"direct": direct_steps, "cot": cot_steps, "tot": tot_steps}
    alternatives = ["organisation par RQ", "organisation par stratégie", "organisation par risque"] if strategy == "tot" else []
    calls = 3 if strategy == "tot" else 1
    return PlanCandidate(
        strategy=strategy,
        objective=objective,
        reasoning_summary=traces[strategy],
        explored_alternatives=alternatives,
        llm_calls=calls,
        steps=plans[strategy],
    )


def controlled_replanner(plan: PlanCandidate, failed_step: PlanStep, available_facets: set[str]) -> PlanCandidate:
    revised_steps = []
    for step in plan.steps:
        if step.id != failed_step.id:
            revised_steps.append(step)
            continue
        supported = [facet for facet in step.required_facets if facet in available_facets]
        revised_steps.append(step.model_copy(update={
            "objective": "Synthétiser les mécanismes de contrôle étayés et signaler explicitement l'absence de validation prospective.",
            "required_facets": supported or ["human_oversight"],
            "mode": "limitation",
        }))
    return plan.model_copy(update={"steps": revised_steps})


def build_report_markdown(execution: ExecutionResult, evidence: list[EvidenceItem]) -> str:
    """Assemble les sections exécutées en une note pédagogique traçable."""
    evidence_by_id = {item.id: item for item in evidence}
    step_by_id = {step.id: step for step in execution.plan.steps}
    lines = [
        "# Note de synthèse pédagogique", "", "## Périmètre", "",
        "Cette note illustre Plan-and-Execute sur un mini-corpus non exhaustif. Elle ne constitue pas une SLR publiable. Chaque affirmation provient des preuves autorisées issues du TD06.", "",
    ]
    for section in execution.sections:
        step = step_by_id[section.step_id]
        question = evidence_by_id[step.evidence_ids[0]].research_question
        lines.extend([f"## {step.rq_id} — {question}", "", "### Réponse synthétique", "", section.content, "", "### Traçabilité des preuves", ""])
        for evidence_id in step.evidence_ids:
            item = evidence_by_id[evidence_id]
            paper_id = item.paper_id
            lines.extend([
                f"- **{item.paper_title}** — `{paper_id}`, page {item.page}, preuve `{item.id}`",
                f"  - Donnée extraite : {item.text}",
                f"  - Limite : {item.limitation}",
            ])
        lines.append("")
    if execution.status == "completed":
        lines.extend(["## Conclusion", "", "Les trois questions ont été traitées dans le périmètre du mini-corpus. Lorsque les preuves étaient insuffisantes, la note a explicité la limite au lieu d'inventer une réponse."])
    else:
        lines.extend(["## Note incomplète", "", "L'exécution s'est arrêtée par abstention ou épuisement du budget. Les sections non exécutées ne sont pas rédigées."])
    return "\n".join(lines)
