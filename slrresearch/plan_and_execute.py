from collections.abc import Callable

from .planning_models import (
    EvidenceItem,
    ExecutionEvent,
    ExecutionResult,
    PlanCandidate,
    PlanningAnalysis,
    PlanMetrics,
    PlanStep,
    StepResult,
)


Planner = Callable[[str, str, list[EvidenceItem]], PlanCandidate]
Replanner = Callable[[PlanCandidate, PlanStep, set[str]], PlanCandidate]

STRATEGY_RQ_ORDER = {
    "direct": ["RQ1", "RQ2", "RQ3"],
    "cot": ["RQ3", "RQ1", "RQ2"],
    "tot": ["RQ2", "RQ1", "RQ3"],
}

def apply_strategy_protocol(plan: PlanCandidate, strategy: str) -> PlanCandidate:
    """Normalise l'ordre et les dépendances pour comparer les stratégies."""
    by_rq = {step.rq_id: step for step in plan.steps}
    ordered = [by_rq[rq_id] for rq_id in STRATEGY_RQ_ORDER[strategy]]

    if strategy in {"direct", "cot"}:
        steps = [
            step.model_copy(
                update={"depends_on": [ordered[i - 1].id] if i else []}
            )
            for i, step in enumerate(ordered)
        ]
    else:
        steps = [
            ordered[0].model_copy(update={"depends_on": []}),
            ordered[1].model_copy(update={"depends_on": []}),
            ordered[2].model_copy(
                update={"depends_on": [ordered[0].id, ordered[1].id]}
            ),
        ]

    summary = {
        "direct": ["Plan linéaire dans l'ordre des questions."],
        "cot": ["Plan structuré dans l'ordre contrôle, performances, compromis."],
        "tot": ["Deux branches sont comparées avant une synthèse finale."],
    }
    alternatives = (
        ["organisation par RQ", "organisation par stratégie", "organisation par risque"]
        if strategy == "tot"
        else []
    )
    return plan.model_copy(
        update={
            "strategy": strategy,
            "steps": steps,
            "reasoning_summary": summary[strategy],
            "explored_alternatives": alternatives,
        }
    )


def build_planning_prompt(
    strategy: str, objective: str, evidence: list[EvidenceItem]
) -> str:
    """TODO 1 — Même spécification, guidage propre à la stratégie."""
    # Remplacer les trois None par les consignes précisées dans l'énoncé.
    instructions = {"direct": None, "cot": None, "tot": None}
    if strategy not in instructions:
        raise ValueError(f"Stratégie inconnue : {strategy}")
    evidence_catalog = [
        {
            "id": item.id,
            "rq_id": item.rq_id,
            "facets": item.facets,
            "finding": item.finding or item.text,
        }
        for item in evidence
    ]
    return (
        f"Objectif : {objective}\n"
        f"Catalogue des preuves autorisées : {evidence_catalog}\n"
        "Contraintes : créer exactement une étape principale pour chacune de RQ1, RQ2 et RQ3 ; "
        "citer uniquement les preuves associées à la RQ de l'étape ; citer uniquement les preuves "
        "autorisées ; déclarer les dépendances ; retourner un PlanCandidate JSON.\n"
        f"Le champ strategy doit être exactement : {strategy}.\n"
        f"Ordre expérimental obligatoire des RQ : {' → '.join(STRATEGY_RQ_ORDER[strategy])}.\n"
        "Le plan doit contenir une seule étape par RQ, dans cet ordre exact.\n"
        f"Méthode : {instructions[strategy]}"
    )


def validate_plan(
    plan: PlanCandidate, allowed_evidence_ids: set[str], required_rqs: set[str]
) -> None:
    """TODO 2 — Contrôles bloquants avant toute exécution."""
    # Remplacer les conditions TODO 2a à 2f par les contrôles de l'énoncé.
    # Une seule étape principale doit répondre à chaque RQ afin d'éviter
    # de produire deux fois la même section dans la note pédagogique.
    step_ids = [step.id for step in plan.steps]
    if False:  # TODO 2a — identifiants dupliqués
        raise ValueError("Identifiants d'étapes dupliqués")
    known_steps: set[str] = set()
    planned_rqs: set[str] = set()
    for step in plan.steps:
        if False:  # TODO 2b — une seule section par RQ
            raise ValueError("Question de recherche répétée dans le plan")
        if False:  # TODO 2c — preuve non autorisée
            raise ValueError("Preuve inconnue dans le plan")
        if False:  # TODO 2e — dépendance vers soi-même
            raise ValueError("Une étape ne peut pas dépendre d'elle-même")
        if False:  # TODO 2d — dépendance inconnue ou située après l'étape
            raise ValueError("Dépendance inconnue ou placée après l'étape")
        known_steps.add(step.id)
        planned_rqs.add(step.rq_id)
    if False:  # TODO 2f — RQ obligatoire absente
        raise ValueError("Questions de recherche non couvertes")


def evaluate_plan(
    plan: PlanCandidate, allowed_evidence_ids: set[str], required_rqs: set[str]
) -> PlanMetrics:
    """Fonction fournie — Mesurer validité, couverture et cohérence."""
    errors: list[str] = []
    try:
        validate_plan(plan, allowed_evidence_ids, required_rqs)
    except ValueError as exc:
        errors.append(str(exc))
    planned_rqs = {step.rq_id for step in plan.steps}
    complete_steps = [
        step
        for step in plan.steps
        if step.objective and step.evidence_ids and step.required_facets
    ]
    positions = {step.id: index for index, step in enumerate(plan.steps)}
    dependencies = [
        (step.id, dependency)
        for step in plan.steps
        for dependency in step.depends_on
    ]
    valid_dependencies = [
        pair
        for pair in dependencies
        if pair[1] in positions and positions[pair[1]] < positions[pair[0]]
    ]
    rq_coverage = len(planned_rqs & required_rqs) / max(1, len(required_rqs))
    section_coverage = len(complete_steps) / max(1, len(plan.steps))
    consistency = len(valid_dependencies) / max(1, len(dependencies)) if dependencies else 1.0
    return PlanMetrics(
        valid=not errors,
        plan_validity_rate=1.0 if not errors else 0.0,
        rq_coverage=rq_coverage,
        section_coverage=section_coverage,
        consistency=consistency,
        errors=errors,
    )


def compare_planning_strategies(
    planner: Planner,
    objective: str,
    evidence: list[EvidenceItem],
    required_rqs: set[str],
) -> list[dict]:
    """TODO 3 — Trois stratégies, mêmes entrées et mêmes critères."""
    allowed = {item.id for item in evidence}
    comparisons = []
    # TODO 3a — Remplacer [] par ["direct", "cot", "tot"].
    for strategy in []:
        plan = planner(strategy, objective, evidence)
        metrics = evaluate_plan(plan, allowed, required_rqs)
        # TODO 3b — Conserver le plan et ses métriques dans un même résultat.
        comparisons.append({"strategy": strategy, "plan": plan, "metrics": metrics})
    return comparisons


def execute_step(
    step: PlanStep,
    evidence_by_id: dict[str, EvidenceItem],
    completed_steps: set[str],
) -> StepResult:
    """TODO 4 — Permissions, préconditions puis exécution."""
    # TODO 4 — Compléter les expressions 4a à 4d marquées ci-dessous.
    # 1. Les dépendances doivent être dans completed_steps.
    # 2. Les preuves demandées doivent exister dans evidence_by_id.
    if not set(step.depends_on) <= None:  # TODO 4a
        return StepResult(
            step_id=step.id,
            status="blocked",
            content="Préconditions non satisfaites.",
            citations=[],
            covered_facets=[],
            missing_facets=step.required_facets,
            tool_calls=0,
        )
    if not set(step.evidence_ids) <= None:  # TODO 4b
        raise ValueError("Preuve non autorisée pendant l'exécution")

    selected = [evidence_by_id[identifier] for identifier in step.evidence_ids]
    available = {facet for item in selected for facet in item.facets}
    covered = sorted(set(step.required_facets) & available)
    missing = sorted(set(step.required_facets) - None)  # TODO 4c
    citations = sorted({item.paper_id for item in selected})

    if missing and step.mode == None:  # TODO 4d
        return StepResult(
            step_id=step.id,
            status="insufficient_evidence",
            content="Preuves insuffisantes pour une synthèse complète.",
            citations=citations,
            covered_facets=covered,
            missing_facets=missing,
        )

    content = " ".join(item.finding or item.text for item in selected)
    if step.mode == "limitation":
        content += f" Limite scientifique explicitée par le plan révisé : {step.objective}"
    return StepResult(step_id=step.id, status="success", content=content, citations=citations, covered_facets=covered, missing_facets=missing)


def observe_step(result: StepResult, allowed_papers: set[str], budget_remaining: int) -> dict:
    """Fonction fournie — Mesures observables avant toute décision."""
    total = len(result.covered_facets) + len(result.missing_facets)
    return {
        "step_success": result.status == "success",
        "evidence_coverage": len(result.covered_facets) / max(1, total),
        "citation_validity": set(result.citations) <= allowed_papers,
        "budget_remaining": budget_remaining,
    }


def run_classic(
    plan: PlanCandidate,
    evidence: list[EvidenceItem],
    required_rqs: set[str],
    max_retries: int = 1,
    max_actions: int = 6,
) -> ExecutionResult:
    """TODO 5 — RETRY borné, plan strictement inchangé."""
    allowed_ids = {item.id for item in evidence}
    validate_plan(plan, allowed_ids, required_rqs)
    evidence_by_id = {item.id: item for item in evidence}
    allowed_papers = {item.paper_id for item in evidence}
    completed: set[str] = set()
    sections: list[StepResult] = []
    trace: list[ExecutionEvent] = []
    actions = 0

    for step in plan.steps:
        attempt = 0
        while True:
            if actions >= max_actions:
                return ExecutionResult(
                    variant="classic", status="budget_exhausted", plan=plan,
                    sections=sections, trace=trace, tool_calls=actions,
                )
            attempt += 1
            actions += 1
            result = execute_step(step, evidence_by_id, completed)
            observation = observe_step(result, allowed_papers, max_actions - actions)
            if observation["step_success"] and None:  # TODO 5a — citation valide
                completed.add(step.id); sections.append(result)
                trace.append(ExecutionEvent(step_id=step.id, attempt=attempt, decision="continue", reason="Étape conforme."))
                break
            if attempt <= None:  # TODO 5b — nombre maximal de retries
                trace.append(ExecutionEvent(step_id=step.id, attempt=attempt, decision="retry", reason="Réessayer sans modifier le plan.", missing_facets=result.missing_facets))
                continue
            trace.append(ExecutionEvent(step_id=step.id, attempt=attempt, decision="abstain", reason="Plan fixe : aucune révision autorisée.", missing_facets=result.missing_facets))
            return ExecutionResult(variant="classic", status="abstained", plan=plan, sections=sections, trace=trace, tool_calls=actions)

    trace.append(ExecutionEvent(step_id=plan.steps[-1].id, attempt=1, decision="finish", reason="Toutes les étapes sont terminées."))
    return ExecutionResult(variant="classic", status="completed", plan=plan, sections=sections, trace=trace, tool_calls=actions)


def run_with_replanning(
    plan: PlanCandidate,
    evidence: list[EvidenceItem],
    required_rqs: set[str],
    replanner: Replanner,
    max_revisions: int = 1,
    max_actions: int = 6,
) -> ExecutionResult:
    """TODO 6 — REPLAN, revalidation et reprise contrôlée."""
    allowed_ids = {item.id for item in evidence}
    evidence_by_id = {item.id: item for item in evidence}
    allowed_papers = {item.paper_id for item in evidence}
    current_plan = plan.model_copy(deep=True)
    validate_plan(current_plan, allowed_ids, required_rqs)
    completed: set[str] = set()
    sections: list[StepResult] = []
    trace: list[ExecutionEvent] = []
    revisions = 0
    actions = 0
    index = 0

    while index < len(current_plan.steps):
        if actions >= max_actions:
            return ExecutionResult(
                variant="replanning", status="budget_exhausted", plan=current_plan,
                sections=sections, trace=trace, revisions=revisions,
                tool_calls=actions,
            )
        step = current_plan.steps[index]
        actions += 1
        result = execute_step(step, evidence_by_id, completed)
        observation = observe_step(result, allowed_papers, max_actions - actions)
        if observation["step_success"] and observation["citation_validity"]:
            completed.add(step.id)
            sections.append(result)
            trace.append(ExecutionEvent(step_id=step.id, attempt=1, decision="continue", reason="Étape conforme."))
            index += 1
            continue
        can_replan = None  # TODO 6a : revisions < max_revisions
        if can_replan and observation["budget_remaining"] > 0:
            trace.append(ExecutionEvent(step_id=step.id, attempt=1, decision="replan", reason="Plan restant inadapté.", missing_facets=result.missing_facets))
            completed_before = {item.id for item in current_plan.steps[:index]}
            current_plan = None  # TODO 6b : appeler replanner avec plan, étape et facettes couvertes
            if not None:  # TODO 6c — les identifiants terminés doivent rester présents
                raise ValueError("Le replanning a supprimé une étape déjà terminée")
            validate_plan(current_plan, allowed_ids, required_rqs)
            revisions += 1
            continue
        trace.append(ExecutionEvent(step_id=step.id, attempt=1, decision="abstain", reason="Aucune révision admissible.", missing_facets=result.missing_facets))
        return ExecutionResult(variant="replanning", status="abstained", plan=current_plan, sections=sections, trace=trace, revisions=revisions, tool_calls=actions)

    trace.append(ExecutionEvent(step_id=current_plan.steps[-1].id, attempt=1, decision="finish", reason="Plan révisé exécuté."))
    return ExecutionResult(variant="replanning", status="completed", plan=current_plan, sections=sections, trace=trace, revisions=revisions, tool_calls=actions)


def build_llm_planner(model):
    """TODO 1 — Construire réellement Direct, CoT structuré et ToT."""
    structured = model.with_structured_output(PlanCandidate)
    analysis_model = model.with_structured_output(PlanningAnalysis)

    def planner(strategy: str, objective: str, evidence: list[EvidenceItem]) -> PlanCandidate:
        prompt = build_planning_prompt(strategy, objective, evidence)
        allowed = {item.id for item in evidence}
        required_rqs = {item.rq_id for item in evidence}

        def invoke_plan(text):
            result = structured.invoke(text)
            return (
                result
                if isinstance(result, PlanCandidate)
                else PlanCandidate.model_validate(result)
            )

        if strategy == "direct":
            # TODO 1a — Un seul appel : produire directement un PlanCandidate.
            plan = None
            calls = 1
        elif strategy == "cot":
            # TODO 1b — Deux appels : PlanningAnalysis, puis PlanCandidate.
            analysis = None
            plan = None
            calls = 2
        else:
            # TODO 1c — Trois appels : produire trois candidats, les valider,
            # puis sélectionner celui dont les métriques sont les meilleures.
            candidates = []
            plan = None
            calls = 3

        plan = plan.model_copy(update={"strategy": strategy, "llm_calls": calls})
        validate_plan(plan, allowed, required_rqs)
        return apply_strategy_protocol(plan, strategy)

    return planner
