from typing import Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    id: str
    rq_id: str
    paper_id: str
    research_question: str = ""
    paper_title: str = ""
    year: int = 0
    study_design: str = ""
    sample: str = ""
    models: list[str] = Field(default_factory=list)
    finding: str = ""
    text: str
    limitation: str = ""
    source_url: str = ""
    facets: list[str]
    page: int = Field(ge=1)


class PlanStep(BaseModel):
    id: str
    rq_id: str
    objective: str
    evidence_ids: list[str] = Field(min_length=1)
    required_facets: list[str] = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    mode: Literal["synthesis", "limitation"] = "synthesis"


class PlanCandidate(BaseModel):
    strategy: Literal["direct", "cot", "tot"]
    objective: str
    steps: list[PlanStep] = Field(min_length=1)
    reasoning_summary: list[str] = Field(default_factory=list)
    explored_alternatives: list[str] = Field(default_factory=list)
    llm_calls: int = Field(default=1, ge=0)

class PlanningAnalysis(BaseModel):
    proposed_order: list[str] = Field(min_length=1)
    rationale: list[str] = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)


class PlanMetrics(BaseModel):
    valid: bool
    plan_validity_rate: float = Field(ge=0, le=1)
    rq_coverage: float = Field(ge=0, le=1)
    section_coverage: float = Field(ge=0, le=1)
    consistency: float = Field(ge=0, le=1)
    errors: list[str] = Field(default_factory=list)


class StepResult(BaseModel):
    step_id: str
    status: Literal["success", "insufficient_evidence", "blocked"]
    content: str
    citations: list[str]
    covered_facets: list[str]
    missing_facets: list[str]
    tool_calls: int = Field(default=1, ge=0)


class ExecutionEvent(BaseModel):
    step_id: str
    attempt: int = Field(ge=1)
    decision: Literal["continue", "retry", "replan", "finish", "abstain"]
    reason: str
    missing_facets: list[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    variant: Literal["classic", "replanning"]
    status: Literal["completed", "abstained", "budget_exhausted"]
    plan: PlanCandidate
    sections: list[StepResult]
    trace: list[ExecutionEvent]
    revisions: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
