"""Explicit human mapping events; candidate discovery never populates decisions."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from evaluation.artifacts import digest_value

REVIEW_CHECKS = (
    "document_identity",
    "variant_equivalence",
    "semantic_support",
    "local_scope",
    "necessary_qualifiers",
    "required_information",
    "table_relationships",
)


class HumanReferenceMapping(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    reference_id: str
    chunk_ids: list[str]
    status: Literal["complete", "partial", "absent", "excluded_complementary"]
    rationale: str = Field(min_length=1)


class HumanMappingDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    question_id: str
    record_sha256: str
    input_sha256: str
    package_sha256: str
    reviewer_id: str = Field(min_length=1)
    reviewed_at: str
    decision: Literal["approved", "rejected", "pending"]
    checks: dict[str, Literal["yes", "no", "doubt", "not_applicable"]]
    references: list[HumanReferenceMapping]
    justification: str = Field(min_length=1)


class HumanMappingLedger:
    def __init__(self, package: dict[str, Any]) -> None:
        body = dict(package)
        declared = body.pop("package_sha256")
        if digest_value(body) != declared:
            raise ValueError("Review package fingerprint mismatch")
        self.package = package
        self.cases = {row["question_id"]: row for row in package["cases"]}
        if len(self.cases) != len(package["cases"]):
            raise ValueError("Duplicate review case")
        self.events: list[HumanMappingDecision] = []

    def append(self, event: HumanMappingDecision) -> None:
        if event.question_id not in self.cases:
            raise ValueError("Unknown or negative mapping question")
        case = self.cases[event.question_id]
        if (
            event.record_sha256 != case["record_sha256"]
            or event.input_sha256 != case["mapping"]["input_sha256"]
            or event.package_sha256 != self.package["package_sha256"]
        ):
            raise ValueError("Human decision belongs to another version/input")
        timestamp = datetime.fromisoformat(event.reviewed_at.replace("Z", "+00:00"))
        if (
            timestamp.tzinfo is None
            or not event.reviewer_id.strip()
            or not event.justification.strip()
        ):
            raise ValueError("Reviewer, rationale and timezone are required")
        if set(event.checks) != set(REVIEW_CHECKS):
            raise ValueError("Incomplete human mapping checklist")
        if any(
            value == "not_applicable" and key != "table_relationships"
            for key, value in event.checks.items()
        ):
            raise ValueError("Only table relationships can be not applicable")
        expected_references = {row["reference_id"] for row in case["references"]}
        if {row.reference_id for row in event.references} != expected_references or len(
            event.references
        ) != len(expected_references):
            raise ValueError(
                "Human mapping must account for every documentary reference"
            )
        allowed_ids = set(case["document_chunk_ids"])
        for reference in event.references:
            if (
                not reference.rationale.strip()
                or len(set(reference.chunk_ids)) != len(reference.chunk_ids)
                or not set(reference.chunk_ids) <= allowed_ids
            ):
                raise ValueError("Invalid, duplicate or foreign human chunk mapping")
            if reference.status in {"complete", "partial"} and not reference.chunk_ids:
                raise ValueError("Support requires explicitly selected chunks")
            if (
                reference.status in {"absent", "excluded_complementary"}
                and reference.chunk_ids
            ):
                raise ValueError(
                    "Unsupported/excluded reference cannot receive gold IDs"
                )
        if event.decision == "approved":
            if any(
                value not in {"yes", "not_applicable"}
                for value in event.checks.values()
            ):
                raise ValueError("Approval cannot conceal failed or doubtful checks")
            if any(
                row.status not in {"complete", "excluded_complementary"}
                for row in event.references
            ) or not any(row.status == "complete" for row in event.references):
                raise ValueError(
                    "Approval requires sufficient human-confirmed documentary support"
                )
            if (
                "table" in case["risk_flags"]
                and event.checks["table_relationships"] != "yes"
            ):
                raise ValueError("Table relations require explicit review")
        self.events.append(event)

    def summary(self) -> dict[str, int]:
        latest = {event.question_id: event for event in self.events}
        return {
            "total": len(self.cases),
            "human_reviewed": len(latest),
            "approved": sum(event.decision == "approved" for event in latest.values()),
            "rejected": sum(event.decision == "rejected" for event in latest.values()),
            "pending": len(self.cases)
            - len(latest)
            + sum(event.decision == "pending" for event in latest.values()),
            "with_doubts": sum(
                "doubt" in event.checks.values() for event in latest.values()
            ),
        }

    def import_export(self, payload: dict[str, Any]) -> None:
        if (
            payload.get("schema_version") != 1
            or payload.get("package_sha256") != self.package["package_sha256"]
        ):
            raise ValueError("Export belongs to another mapping package")
        imported = HumanMappingLedger(self.package)
        for row in payload["events"]:
            imported.append(HumanMappingDecision.model_validate(row))
        old = [event.model_dump() for event in self.events]
        current = [event.model_dump() for event in imported.events]
        if current[: len(old)] != old or payload.get("summary") != imported.summary():
            raise ValueError("Import cannot remove history or falsify review counts")
        self.events = imported.events

    def approved_ids(self) -> dict[str, list[str]]:
        """Inspection only: a complete ledger and authorization must precede freezing."""
        latest = {event.question_id: event for event in self.events}
        return {
            identifier: sorted(
                {
                    chunk
                    for reference in event.references
                    for chunk in reference.chunk_ids
                }
            )
            for identifier, event in latest.items()
            if event.decision == "approved"
        }
