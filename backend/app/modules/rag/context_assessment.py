"""One compact evidence-selection contract, shared by both selection paths."""

import json
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


MAX_EVIDENCE_ITEMS = 6


class EvidenceSupport(StrEnum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    INSUFFICIENT = "insufficient"


class EvidenceLimitation(StrEnum):
    SCOPE = "scope"
    INDIVIDUAL = "individual"
    MISSING = "missing"


class ContextAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_ids: list[str] = Field(max_length=MAX_EVIDENCE_ITEMS)
    limitation: EvidenceLimitation | None

    @classmethod
    def provider_response_format(cls) -> dict[str, object]:
        schema = cls.model_json_schema()
        # The provider supports a JSON Schema subset without maxItems.
        # Keep the six-ID limit in local validation, not in the wire schema.
        schema["properties"]["unit_ids"].pop("maxItems")
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "evidence_selection",
                "strict": True,
                "schema": schema,
            },
        }

    @property
    def support(self) -> EvidenceSupport:
        # No selected evidence always means abstention. A limitation qualifies
        # selected evidence; it cannot make an empty selection partially supported.
        if not self.unit_ids:
            return EvidenceSupport.INSUFFICIENT
        if self.limitation is not None:
            return EvidenceSupport.PARTIALLY_SUPPORTED
        return EvidenceSupport.SUPPORTED


class EvidenceAssessmentDecoder:
    def decode(self, raw_response: str) -> ContextAssessment:
        # Preserve the original JSON position or schema error; no legacy retry.
        payload = json.loads(self._unwrap_json_envelope(raw_response))
        return ContextAssessment.model_validate(payload)

    def _unwrap_json_envelope(self, raw_response: str) -> str:
        """Remove only a complete JSON fence, never extract or repair fragments."""
        response_lines = raw_response.strip().splitlines()
        if len(response_lines) < 3:
            return raw_response
        if response_lines[0] not in {"```json", "```"}:
            return raw_response
        if response_lines[-1] != "```":
            return raw_response

        json_lines = response_lines[1:-1]
        if any(line.strip().startswith("```") for line in json_lines):
            return raw_response
        # JSON syntax, schema and source-ID checks still validate the entire body.
        return "\n".join(json_lines)
