"""Resumable runner skeleton, restricted to offline fixture adapters for now."""

from __future__ import annotations

import json
import math
import os
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol

from evaluation.artifacts import digest_value, read_jsonl
from evaluation.contracts import (
    RankedChunk,
    RetrievalJob,
    RetrievalRequest,
    Scenario,
    Strategy,
)
from evaluation.dataset import DocumentIdentity, FrozenCollection


def plan_retrieval_jobs(collection: FrozenCollection) -> tuple[RetrievalJob, ...]:
    document_lookup = {document.key: document for document in collection.documents}
    jobs: list[RetrievalJob] = []
    for record in collection.records.values():
        if not record["answerable"]:
            continue
        target = document_lookup[f"{record['corpus_id']}/{record['document_id']}"]
        scenarios: tuple[tuple[Scenario, str], ...] = (
            ("scoped", "question_scoped"),
            ("cross", "question_cross_bula"),
        )
        strategies: tuple[Strategy, ...] = ("dense", "bm25", "hybrid")
        for scenario, question_field in scenarios:
            for strategy in strategies:
                jobs.append(
                    RetrievalJob(
                        record["question_id"],
                        digest_value(record),
                        target,
                        scenario,
                        strategy,
                        record[question_field],
                    )
                )
    return tuple(jobs)


class OfflineRetriever(Protocol):
    is_offline: bool

    def retrieve(
        self, request: RetrievalRequest, strategy: str
    ) -> tuple[RankedChunk, ...]: ...


class OfflineRetrievalRunner:
    def __init__(
        self,
        *,
        checkpoint_path: Path,
        snapshot_sha256: str,
        universe: tuple[DocumentIdentity, ...],
        jobs: Iterable[RetrievalJob],
    ) -> None:
        self.path = checkpoint_path
        self.snapshot_sha256 = snapshot_sha256
        self.universe = universe
        self.jobs = tuple(jobs)
        if len({job.key for job in self.jobs}) != len(self.jobs):
            raise ValueError("Duplicate job key")
        self.plan_sha256 = digest_value(
            {
                "jobs": [asdict(job) for job in self.jobs],
                "universe": [asdict(document) for document in universe],
            }
        )

    def run(self, adapter: OfflineRetriever) -> list[dict[str, Any]]:
        if not adapter.is_offline:
            raise ValueError("External execution is not authorized in this preparation")
        previous = read_jsonl(self.path) if self.path.exists() else []
        job_lookup = {job.key: job for job in self.jobs}
        seen: set[str] = set()
        for record in previous:
            if (
                record["snapshot_sha256"] != self.snapshot_sha256
                or record["plan_sha256"] != self.plan_sha256
            ):
                raise ValueError("Checkpoint configuration/snapshot mismatch")
            if record["job_key"] not in job_lookup or record["job_key"] in seen:
                raise ValueError("Unknown or duplicate checkpoint job")
            if record["record_sha256"] != job_lookup[record["job_key"]].record_sha256:
                raise ValueError("Checkpoint record version mismatch")
            if record["entry_sha256"] != digest_value(
                {key: value for key, value in record.items() if key != "entry_sha256"}
            ):
                raise ValueError("Checkpoint entry was changed")
            seen.add(record["job_key"])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        results = list(previous)
        for job in self.jobs:
            if job.key in seen:
                continue  # Includes recorded failures: no automatic retries/substitutions.
            started = perf_counter()
            record = {
                "execution_mode": "offline_fixture",
                "job_key": job.key,
                "record_sha256": job.record_sha256,
                "snapshot_sha256": self.snapshot_sha256,
                "plan_sha256": self.plan_sha256,
                "request": asdict(job.request()),
                "strategy": job.strategy,
            }
            failure_stage = "retrieval"
            try:
                ranking = adapter.retrieve(job.request(), job.strategy)
                failure_stage = "ranking_validation"
                self._validate_ranking(job, ranking)
                record.update(
                    status="success",
                    ranking=[asdict(chunk) for chunk in ranking],
                    technical_failure=None,
                    failure_stage=None,
                )
            except Exception as error:
                record.update(
                    status="technical_failure",
                    ranking=None,
                    technical_failure=type(error).__name__,
                    failure_stage=failure_stage,
                )
            record["latency_ms"] = (perf_counter() - started) * 1000
            record["entry_sha256"] = digest_value(record)
            with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(
                    json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n"
                )
                stream.flush()
                os.fsync(stream.fileno())
            results.append(record)
        return results

    def _validate_ranking(
        self, job: RetrievalJob, ranking: tuple[RankedChunk, ...]
    ) -> None:
        documents = {document.key: document for document in self.universe}
        if job.target.key not in documents or documents[job.target.key] != job.target:
            raise ValueError("Job target is outside the snapshot")
        if len(ranking) > 10 or [chunk.rank for chunk in ranking] != list(
            range(1, len(ranking) + 1)
        ):
            raise ValueError(
                "Ranking must preserve contiguous backend positions up to ten"
            )
        if len({chunk.chunk_id for chunk in ranking}) != len(ranking):
            raise ValueError("Duplicate ranked chunk")
        for chunk in ranking:
            document = documents.get(f"{chunk.corpus_id}/{chunk.document_id}")
            if (
                document is None
                or document.pdf_sha256 != chunk.pdf_sha256
                or chunk.corpus_id != job.target.corpus_id
            ):
                raise ValueError("Ranked document is outside the authorized corpus")
            if job.scenario == "scoped" and chunk.document_id != job.target.document_id:
                raise ValueError("Scoped ranking contains another PDF")
            if not math.isfinite(chunk.score) or not all(
                math.isfinite(value) for value in chunk.score_details.values()
            ):
                raise ValueError("Nonfinite score")
