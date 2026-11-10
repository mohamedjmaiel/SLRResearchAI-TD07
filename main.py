from pathlib import Path

from slrresearch.plan_and_execute import compare_planning_strategies, run_classic, run_with_replanning
from slrresearch.td07_runtime import build_report_markdown, controlled_planner, controlled_replanner, load_td06_handoff


OBJECTIVE = "Produire une note pédagogique couvrant RQ1, RQ2 et RQ3."


def main():
    root = Path(__file__).parent
    evidence, required_rqs = load_td06_handoff(root / "artifacts" / "td06_evidence.json")
    comparisons = compare_planning_strategies(controlled_planner, OBJECTIVE, evidence, required_rqs)
    print("\n=== PHASE A — DIRECT / CoT / ToT ===")
    for item in comparisons:
        print(item["strategy"], item["metrics"].model_dump(), "LLM calls:", item["plan"].llm_calls)
    direct = comparisons[0]["plan"]
    classic = run_classic(direct, evidence, required_rqs)
    adaptive = run_with_replanning(direct, evidence, required_rqs, controlled_replanner)
    print("\n=== PHASE B — MÊME PLAN DIRECT ===")
    print("Classique :", classic.status, "révisions:", classic.revisions, "appels:", classic.tool_calls)
    print("Replanning :", adaptive.status, "révisions:", adaptive.revisions, "appels:", adaptive.tool_calls)
    print("\n=== RAPPORT FINAL APRÈS REPLANNING ===")
    print(build_report_markdown(adaptive, evidence))


if __name__ == "__main__":
    main()
