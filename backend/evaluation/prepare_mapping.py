"""Prepare an offline mapping/review package or validate an explicit human export."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import json
import os
from pathlib import Path
import platform
import socket
from typing import Any
from unittest.mock import patch
from urllib.parse import quote

from evaluation.artifacts import digest_file, digest_value, read_json, write_new_json
from evaluation.contracts import EvidenceReference, MappingInput
from evaluation.evidence_mapping import CandidatePolicy, EvidenceCandidateMapper, tokens
from evaluation.mapping_review import HumanMappingLedger
from evaluation.mapping_sources import FrozenMappingSources


def documentary_region_text(value: object) -> str | None:
    """Lossless JSON representation for structured regions in the existing contract."""
    if value is None or isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def documentary_presence(
    literal_markdown: bool, literal_any_chunk: bool, literal_source_chunk: bool
) -> str:
    """Metadata-only correspondence is not a disappearance from the index."""
    if literal_any_chunk and not literal_source_chunk:
        return "literal_in_metadata_only_requires_documentary_confirmation"
    if literal_markdown and not literal_any_chunk:
        return "source_quote_in_markdown_without_full_chunk_correspondence"
    if not literal_markdown:
        return "source_quote_not_literal_in_parsed_markdown"
    return "literal_correspondence_pending_semantic_review"


def candidate_has_recorded_fallback(detail: dict[str, Any]) -> bool:
    # The indexed method is "deterministic", not "fallback". The reason records
    # why primary chunking was replaced, not a failure of the indexed chunk.
    return bool(detail.get("metadata", {}).get("fallback_reason"))


class MappingPackageBuilder:
    def __init__(
        self, sources: FrozenMappingSources, policy: CandidatePolicy = CandidatePolicy()
    ) -> None:
        self.sources = sources
        self.policy = policy

    def build(self, output: Path) -> dict[str, Any]:
        if output.exists():
            raise ValueError(
                "Mapping packages are immutable; use a fresh output directory"
            )
        mapper = EvidenceCandidateMapper(self.policy)
        cases, negatives, inputs = [], [], []
        for identifier, record in sorted(self.sources.records.items()):
            if not record["answerable"]:
                negatives.append(
                    {
                        "question_id": identifier,
                        "record_sha256": self.sources.record_hashes[identifier],
                        "corpus_id": record["corpus_id"],
                        "document_id": record["document_id"],
                        "question_scoped": record["question_scoped"],
                        "question_cross_bula": record["question_cross_bula"],
                        "absence_rationale": record.get("absence_rationale"),
                        "gold_chunk_ids": [],
                        "policy": "negative_abstention_scoped_only_not_positive_mapping",
                    }
                )
                continue
            key = f"{record['corpus_id']}/{record['document_id']}"
            references = tuple(
                EvidenceReference(
                    f"R{index:02}",
                    row["quote"],
                    row["pdf_page"],
                    row["section"],
                    documentary_region_text(row.get("source_region")),
                )
                for index, row in enumerate(record["reference_evidence"], 1)
            )
            if not references:
                raise ValueError("A positive question requires documentary references")
            mapping_input = MappingInput(
                identifier,
                self.sources.record_hashes[identifier],
                digest_file(self.sources.snapshot_path),
                self.sources.documents[key],
                record["question_scoped"],
                record["question_cross_bula"],
                record["expected_information"],
                tuple(record["required_qualifiers"]),
                references,
                self.sources.chunks[key],
            )
            mapping, candidates = mapper.discover(mapping_input)
            documentary_checks = []
            for reference, match in zip(references, mapping.matches, strict=True):
                quote_tokens = tokens(reference.quote)
                literal, _, _ = mapper.match_token_sequences(
                    quote_tokens, tokens(self.sources.markdown[key])
                )
                full_any_chunk = any(
                    candidate.method
                    in {"literal_token_sequence", "adjacent_literal_token_sequence"}
                    for candidate in candidates[reference.reference_id]
                )
                full_chunk_match = any(
                    candidate.method
                    in {"literal_token_sequence", "adjacent_literal_token_sequence"}
                    and candidate.source_role == "source_text"
                    for candidate in candidates[reference.reference_id]
                )
                documentary_checks.append(
                    {
                        "reference_id": reference.reference_id,
                        "literal_tokens_in_parsed_markdown": literal,
                        "literal_tokens_in_indexed_chunks": full_any_chunk,
                        "literal_tokens_in_source_text_chunks": full_chunk_match,
                        "diagnostic": documentary_presence(
                            literal, full_any_chunk, full_chunk_match
                        ),
                        "page_binding": "reference_page_only_not_inferred_for_chunks",
                    }
                )
            annotation = self.sources.annotations[identifier]
            flags = ["page_provenance_unavailable", "semantic_review_required"]
            details = self.sources.details
            selected = {
                chunk
                for group in candidates.values()
                for candidate in group
                for chunk in candidate.chunk_ids
            }
            if len(references) > 1:
                flags.append("multiple_references")
            if any(
                len(tokens(reference.quote)) < self.policy.minimum_partial_tokens
                for reference in references
            ):
                flags.append("short_quote_requires_context")
            if any("|" in details[chunk]["text"] for chunk in selected) or any(
                "tabela" in row.section.casefold()
                or any(
                    label in (row.source_region or "").casefold()
                    for label in ("tabela", "table")
                )
                for row in references
            ):
                flags.append("table")
            if self.sources.checkpoints[key].get("fallback", {}).get("count", 0):
                flags.append("document_has_chunking_fallback")
            if any(
                candidate_has_recorded_fallback(details[chunk]) for chunk in selected
            ):
                flags.append("candidate_from_fallback")
            if any(
                len(candidate.chunk_ids) > 1
                for group in candidates.values()
                for candidate in group
            ):
                flags.append("fragmented_candidate")
            if any(
                candidate.source_role != "source_text"
                for group in candidates.values()
                for candidate in group
            ):
                flags.append("metadata_candidate")
            document = self.sources.documents[key]
            pdf_path = self.sources.root / document.relative_path
            pdf_link = quote(
                os.path.relpath(pdf_path, output).replace("\\", "/"), safe="/:"
            )
            case = {
                "question_id": identifier,
                "record_sha256": self.sources.record_hashes[identifier],
                "medication": record["medication"],
                "corpus_id": record["corpus_id"],
                "document_id": record["document_id"],
                "pdf_sha256": document.pdf_sha256,
                "pdf_link": pdf_link,
                "question_scoped": record["question_scoped"],
                "question_cross_bula": record["question_cross_bula"],
                "source_revision": record["draft_revision"],
                "derived_revision": record["derived_revision"],
                "expected_information": record["expected_information"],
                "required_qualifiers": record["required_qualifiers"],
                "human_question_annotation": {
                    field: annotation[field]
                    for field in (
                        "required_information",
                        "complementary_information",
                        "justification",
                    )
                },
                "references": [asdict(reference) for reference in references],
                "mapping": asdict(mapping),
                "documentary_checks": documentary_checks,
                "candidates": {
                    reference_id: [asdict(candidate) for candidate in group]
                    for reference_id, group in candidates.items()
                },
                "document_chunk_ids": [
                    chunk.chunk_id for chunk in mapping_input.chunks
                ],
                "risk_flags": flags,
                "authorship_flags": record.get("review_flags", []),
                "approved_chunk_ids": [],
                "human_mapping_status": "pending",
            }
            inputs.append(asdict(mapping_input))
            cases.append(case)
        package = {
            "schema_version": 1,
            "tool_version": "offline_mapping_v1.3",
            "candidate_policy": asdict(self.policy),
            "derived_release_fingerprint": self.sources.release["fingerprint_sha256"],
            "ingestion_snapshot_fingerprint": self.sources.snapshot[
                "fingerprint_sha256"
            ],
            "ingestion_snapshot_file_sha256": digest_file(self.sources.snapshot_path),
            "input_files": self.sources.files,
            "cases": cases,
            "negatives": negatives,
            "chunk_catalog": self.sources.details,
            "semantics": "Lexical candidates only; all 160 mappings require explicit independent human approval.",
            "runtime": {
                "python": platform.python_version(),
                "implementation": platform.python_implementation(),
            },
        }
        package["package_sha256"] = digest_value(package)
        summary = self.summarize(package)
        self.sources.verify_unchanged()
        output.mkdir(parents=True)
        write_new_json(output / "review-package.json", package)
        for name, rows in (
            ("mapping-inputs.jsonl", inputs),
            ("candidates.jsonl", cases),
            ("negatives.jsonl", negatives),
        ):
            with (output / name).open("x", encoding="utf-8", newline="\n") as stream:
                for row in rows:
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        write_new_json(output / "coverage.json", summary)
        self._render(output, package)
        self._report(output, summary, cases)
        manifest = {
            "schema_version": 1,
            "status": "candidates_pending_human_mapping_review",
            "package_sha256": package["package_sha256"],
            "ingestion_snapshot_fingerprint": package["ingestion_snapshot_fingerprint"],
            "derived_release_fingerprint": package["derived_release_fingerprint"],
            "candidate_policy": asdict(self.policy),
            "input_files": self.sources.files,
            "tool_files": {
                path.relative_to(Path(__file__).parent).as_posix(): digest_file(path)
                for path in sorted(
                    [
                        *Path(__file__).parent.glob("*mapping*.py"),
                        *(
                            Path(__file__).parent / name
                            for name in ("artifacts.py", "contracts.py", "dataset.py")
                        ),
                        *(Path(__file__).parent / "mapping_ui").iterdir(),
                    ]
                )
                if path.is_file()
            },
            "artifacts": {
                path.name: digest_file(path)
                for path in sorted(output.iterdir())
                if path.is_file()
            },
            "human_mapping_decisions": 0,
            "definitive_mapping": False,
        }
        manifest["fingerprint_sha256"] = digest_value(manifest)
        write_new_json(output / "manifest.json", manifest)
        self.sources.verify_unchanged()
        return summary

    @staticmethod
    def summarize(package: dict[str, Any]) -> dict[str, Any]:
        cases = package["cases"]
        return {
            "positives": len(cases),
            "negatives_separate": len(package["negatives"]),
            "with_any_candidates": sum(
                any(match["chunk_ids"] for match in case["mapping"]["matches"])
                for case in cases
            ),
            "all_references_with_candidates": sum(
                all(match["chunk_ids"] for match in case["mapping"]["matches"])
                for case in cases
            ),
            "lexical_status_counts": dict(
                Counter(case["mapping"]["status"] for case in cases)
            ),
            "per_corpus": {
                corpus: dict(
                    Counter(
                        case["mapping"]["status"]
                        for case in cases
                        if case["corpus_id"] == corpus
                    )
                )
                for corpus in ("A", "B")
            },
            "reference_status_counts": dict(
                Counter(
                    match["status"]
                    for case in cases
                    for match in case["mapping"]["matches"]
                )
            ),
            "documentary_diagnostic_counts": dict(
                Counter(
                    check["diagnostic"]
                    for case in cases
                    for check in case["documentary_checks"]
                )
            ),
            "risk_flag_counts": dict(
                Counter(flag for case in cases for flag in case["risk_flags"])
            ),
            "human_confirmed_questions": 0,
            "human_confirmed_evidence_ids": 0,
            "pending_human_review": len(cases),
            "same_chunk_ids_for_scoped_and_cross": True,
            "retrieval_metrics_computed": False,
        }

    @staticmethod
    def _render(output: Path, package: dict[str, Any]) -> None:
        assets = Path(__file__).parent / "mapping_ui"
        script = (assets / "review.js").read_text(encoding="utf-8")
        template = (assets / "template.html").read_text(encoding="utf-8")
        payload = (
            json.dumps(package, ensure_ascii=False)
            .replace("<", "\\u003c")
            .replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029")
        )
        html = template.replace("__PAYLOAD__", payload).replace("__SCRIPT__", script)
        with (output / "review.html").open("x", encoding="utf-8") as stream:
            stream.write(html)

    @staticmethod
    def _report(
        output: Path, summary: dict[str, Any], cases: list[dict[str, Any]]
    ) -> None:
        lines = [
            "# Offline evidence mapping — candidate review",
            "",
            "No human mapping decisions exist. Lexical completeness is not semantic sufficiency.",
            "",
            f"Positive questions: {summary['positives']}; negatives kept separately: {summary['negatives_separate']}.",
            f"Questions with candidates: {summary['with_any_candidates']}; all references with candidates: {summary['all_references_with_candidates']}.",
            f"Lexical statuses: `{summary['lexical_status_counts']}`. Human-confirmed coverage: **0/160**.",
            "",
            "## Review queue",
            "",
            "| ID | Lexical status | References without candidates | Risk flags |",
            "| --- | --- | --- | --- |",
        ]
        priority = {"absent": 0, "partial": 1, "ambiguous": 2, "complete": 3}
        for case in sorted(
            cases,
            key=lambda case: (priority[case["mapping"]["status"]], case["question_id"]),
        ):
            absent = [
                match["reference_id"]
                for match in case["mapping"]["matches"]
                if not match["chunk_ids"]
            ]
            lines.append(
                f"| {case['question_id']} | {case['mapping']['status']} | {', '.join(absent) or '—'} | {', '.join(case['risk_flags'])} |"
            )
        lines.extend(
            [
                "",
                "## Limits and freezing procedure",
                "",
                "- Page numbers belong to frozen PDF references. Indexed chunks lack reliable physical-page provenance; the mapper does not invent offsets or page associations.",
                "- Text/type matches, section agreement and combined windows locate candidates only. Clinical conditions, table row/column associations and formulation identity require human review.",
                "- Complete means one lexical full-match alternative per reference. Ambiguous means multiple alternatives; these may be harmless overlaps, not errors. Partial/absent does not prove parsing loss.",
                "- Per-reference documentary checks separate quotes found literally in stored Markdown but not as full chunk sequences from quotes not found literally in that Markdown. Neither establishes semantic loss or an incorrect source annotation without review.",
                "- Candidate discovery uses all chunks of the target PDF, in source order. It never reads retrieval results, computes BM25/dense scores, calls models or filters future cross-bula retrieval.",
                "- Original quotes, human indispensable/complementary annotations and qualifiers are shown separately. Excluding a complementary reference requires an explicit human rationale.",
                "- Review all 160 positives; prioritize tables, fragmented/missing references and fallback-origin candidates. The instrument permits inspecting/selecting any chunk of the same target PDF.",
                "- Export explicit human events; validate them with `python -m evaluation.prepare_mapping validate-review`. Old/foreign IDs, versions, missing support and doubtful approvals are rejected.",
                "- Preserve append-only event history. Import is limited to an extension of the current history. No question approval is inherited as mapping approval.",
                "- After human review and separate authorization, bind the effective reference-to-chunk sets, both scenarios, snapshot and release in a new immutable manifest. Do not freeze or execute yet.",
                "- Resolve partial/absent cases or approve an explicit denominator policy before metrics. Never silently remove positives because of an ingestion or mapping failure.",
            ]
        )
        with (output / "report.md").open("x", encoding="utf-8") as stream:
            stream.write("\n".join(lines) + "\n")


def run_cli() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--root", type=Path, required=True)
    prepare.add_argument("--derived-manifest", type=Path, required=True)
    prepare.add_argument("--ingestion-snapshot", type=Path, required=True)
    prepare.add_argument("--snapshot-fingerprint", required=True)
    prepare.add_argument("--output", type=Path, required=True)
    validate = commands.add_parser("validate-review")
    validate.add_argument("--package", type=Path, required=True)
    validate.add_argument("--decisions", type=Path, required=True)
    options = parser.parse_args()
    if options.command == "prepare":
        sources = FrozenMappingSources(
            options.root,
            options.derived_manifest,
            options.ingestion_snapshot,
            options.snapshot_fingerprint,
        )
        print(
            json.dumps(
                MappingPackageBuilder(sources).build(options.output), ensure_ascii=False
            )
        )
    else:
        ledger = HumanMappingLedger(read_json(options.package))
        ledger.import_export(read_json(options.decisions))
        print(json.dumps(ledger.summary()))


def main() -> None:
    with (
        patch.object(
            socket.socket,
            "connect",
            side_effect=RuntimeError("Network is prohibited during offline mapping"),
        ),
        patch.object(
            socket.socket,
            "connect_ex",
            side_effect=RuntimeError("Network is prohibited during offline mapping"),
        ),
    ):
        run_cli()


if __name__ == "__main__":
    main()
