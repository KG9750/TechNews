"""Automatic Briefing Run orchestration primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .contracts import CONNECTOR_STATUSES, BriefingRun, CandidateItem, ContractError
from .source_policy import PolicyDecision, SourceAccessPolicy


@dataclass(frozen=True)
class ConnectorResult:
    source_id: str
    status: str
    candidates: tuple[CandidateItem, ...] = ()
    warning: str | None = None

    def __post_init__(self) -> None:
        if self.status not in CONNECTOR_STATUSES:
            raise ContractError(f"connector status must be one of {sorted(CONNECTOR_STATUSES)}")


@dataclass(frozen=True)
class CandidateExclusion:
    candidate_id: str
    source_id: str
    reason: str
    policy_decision: PolicyDecision


@dataclass(frozen=True)
class RunPreparation:
    run: BriefingRun
    accepted_candidates: tuple[CandidateItem, ...]
    excluded_candidates: tuple[CandidateExclusion, ...]


class AutomaticBriefingRun:
    """Owns first-pass run state and source-policy enforcement."""

    def __init__(self, source_policy: SourceAccessPolicy) -> None:
        self.source_policy = source_policy

    def prepare(
        self,
        *,
        run_id: str,
        domain_template: str,
        scheduled_for: str,
        delivery_deadline: str,
        started_at: str,
        connector_results: tuple[ConnectorResult, ...],
        model_task_status: Mapping[str, object] | None = None,
        archive_status: Mapping[str, object] | None = None,
        feishu_delivery_status: Mapping[str, object] | None = None,
    ) -> RunPreparation:
        connector_status: dict[str, dict[str, object]] = {}
        accepted: list[CandidateItem] = []
        excluded: list[CandidateExclusion] = []
        warnings: list[str] = []

        for result in connector_results:
            connector_status[result.source_id] = {
                "status": result.status,
                "item_count": len(result.candidates),
            }
            if result.warning:
                connector_status[result.source_id]["warning"] = result.warning
                warnings.append(f"{result.source_id}: {result.warning}")
            if result.status == "failed":
                connector_status[result.source_id]["failure_reason"] = result.warning or "connector failed"
            if result.status in {"partial", "timeout", "failed"}:
                warnings.append(f"{result.source_id}: connector status is {result.status}")

            for candidate in result.candidates:
                decision = self.source_policy.evaluate_candidate(candidate)
                if decision.allowed:
                    accepted.append(candidate)
                else:
                    excluded.append(
                        CandidateExclusion(
                            candidate_id=candidate.id,
                            source_id=candidate.source_id,
                            reason=decision.reason,
                            policy_decision=decision,
                        )
                    )

        run = BriefingRun.from_mapping(
            {
                "run_id": run_id,
                "domain_template": domain_template,
                "scheduled_for": scheduled_for,
                "delivery_deadline": delivery_deadline,
                "started_at": started_at,
                "connector_status": connector_status,
                "model_task_status": model_task_status or {},
                "archive_status": archive_status or {},
                "feishu_delivery_status": feishu_delivery_status or {},
                "run_warnings": warnings,
            }
        )
        return RunPreparation(
            run=run,
            accepted_candidates=tuple(accepted),
            excluded_candidates=tuple(excluded),
        )
