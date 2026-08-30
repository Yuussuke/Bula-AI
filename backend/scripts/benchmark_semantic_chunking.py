"""Compare semantic chunking models on six safety-focused leaflet sections."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata
from typing import TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.modules.rag.embeddings import EmbeddingAdapter
    from app.modules.rag.parsers.pdf_parser import BulaParser
    from app.modules.rag.schemas import ChunkResult


DEFAULT_BASELINE_MODEL = "google/gemini-2.5-flash-lite"
DEFAULT_CANDIDATE_MODEL = "google/gemini-3.1-flash-lite"
DEFAULT_OUTPUT_PATH = Path("tmp/semantic-chunking-benchmark/results.json")
FIXTURE_PDF_ROOT = Path("tests/fixtures/rag/bulas")
H2_HEADING_PATTERN = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.MULTILINE)
DOSAGE_VALUE_PATTERN = re.compile(
    r"\b\d+(?:[.,]\d+)?(?:\s*(?:a|-|–)\s*\d+(?:[.,]\d+)?)?\s*"
    r"(?:mg|g|mcg|µg|mL|UI)(?:\s*/\s*(?:kg|mg|g|mL))?\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FocusedSectionSpec:
    document: str
    label: str
    heading_aliases: tuple[str, ...]


@dataclass(frozen=True)
class SourceSection:
    document: str
    label: str
    heading: str
    text: str


FOCUSED_SECTION_SPECS = (
    FocusedSectionSpec("dipirona", "contraindications", ("CONTRAINDICACOES",)),
    FocusedSectionSpec("dipirona", "dosage", ("POSOLOGIA",)),
    FocusedSectionSpec("dipirona", "adverse_effects", ("REACOES ADVERSAS",)),
    FocusedSectionSpec("amoxicilina", "composition", ("COMPOSICAO",)),
    FocusedSectionSpec("amoxicilina", "dosage", ("POSOLOGIA",)),
    FocusedSectionSpec(
        "amoxicilina",
        "adverse_effects",
        ("QUAIS OS MALES QUE ESTE MEDICAMENTO PODE ME CAUSAR?",),
    ),
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare retrieval_v3 with the former and candidate Gemini models "
            "on six focused sections. Calls and models run sequentially."
        )
    )
    parser.add_argument(
        "--dipirona-pdf",
        type=Path,
        default=FIXTURE_PDF_ROOT / "dipirona_sanofi_medley_solucao_oral.pdf",
    )
    parser.add_argument(
        "--amoxicilina-pdf",
        type=Path,
        default=FIXTURE_PDF_ROOT / "amoxicilina_cimed_suspensao_oral.pdf",
    )
    parser.add_argument("--baseline-model", default=DEFAULT_BASELINE_MODEL)
    parser.add_argument("--candidate-model", default=DEFAULT_CANDIDATE_MODEL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    return parser


async def run_benchmark(
    *,
    settings: Settings,
    pdf_paths: dict[str, Path],
    models: Sequence[str],
    output_path: Path,
) -> dict[str, object]:
    from app.modules.rag.chunker import BulaChunker
    from app.modules.rag.dependencies import get_embeddings, get_llm_client
    from app.modules.rag.parsers.pdf_parser import BulaParser
    from app.modules.rag.schemas import ChunkingConfig
    from app.modules.rag.token_estimator import build_token_estimator

    _validate_inputs(pdf_paths=pdf_paths, models=models)
    parser = BulaParser(ocr_enabled=False)
    source_sections = await _load_focused_sections(
        parser=parser,
        pdf_paths=pdf_paths,
    )
    embeddings = get_embeddings(settings=settings)
    llm_client = get_llm_client(settings=settings)

    model_reports: list[dict[str, object]] = []
    for model in models:
        chunker = BulaChunker(
            llm=llm_client,
            config=ChunkingConfig(
                target_tokens=settings.processing.chunk_target_tokens,
                min_tokens=settings.processing.chunk_min_tokens,
                max_tokens=settings.processing.chunk_max_tokens,
                overlap_ratio=0,
                is_batching_enabled=settings.processing.chunk_batch_enabled,
                batch_max_tokens=settings.processing.chunk_batch_max_tokens,
                batch_max_sections=settings.processing.chunk_batch_max_sections,
                model=model,
                request_timeout_seconds=settings.openrouter.chunk_timeout_seconds,
            ),
            token_estimator=build_token_estimator(settings=settings),
        )
        section_reports: list[dict[str, object]] = []
        for source_section in source_sections:
            chunk_result = await chunker.chunk_markdown(
                markdown=source_section.text,
                doc_id=f"benchmark-{source_section.document}-{source_section.label}",
            )
            section_reports.append(
                await _build_section_report(
                    source_section=source_section,
                    chunk_result=chunk_result,
                    embeddings=embeddings,
                )
            )

        model_reports.append(
            {
                "model": model,
                "prompt_version": "retrieval_v3",
                "summary": _summarize_sections(section_reports=section_reports),
                "sections": section_reports,
            }
        )

    report: dict[str, object] = {
        "contract": {
            "prompt_version": "retrieval_v3",
            "temperature": 0,
            "seed": 17,
            "max_output_tokens": 5000,
            "provider": {
                "zdr": True,
                "data_collection": "deny",
                "require_parameters": True,
                "allow_fallbacks": True,
            },
            "inference_mode": "sequential",
            "embeddings_enabled": True,
        },
        "models": model_reports,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


async def _load_focused_sections(
    *,
    parser: BulaParser,
    pdf_paths: dict[str, Path],
) -> list[SourceSection]:
    sections_by_document: dict[str, list[tuple[str, str]]] = {}
    for document, pdf_path in pdf_paths.items():
        parse_result = await parser.parse(
            pdf_bytes=pdf_path.read_bytes(),
            filename=pdf_path.name,
        )
        if not parse_result.success:
            raise RuntimeError(f"Could not parse benchmark PDF: {pdf_path.name}")
        sections_by_document[document] = split_h2_sections(parse_result.markdown)

    return [
        _find_focused_section(
            spec=spec,
            available_sections=sections_by_document[spec.document],
        )
        for spec in FOCUSED_SECTION_SPECS
    ]


def split_h2_sections(markdown: str) -> list[tuple[str, str]]:
    heading_matches = list(H2_HEADING_PATTERN.finditer(markdown))
    sections: list[tuple[str, str]] = []
    for heading_index, heading_match in enumerate(heading_matches):
        section_end = (
            heading_matches[heading_index + 1].start()
            if heading_index + 1 < len(heading_matches)
            else len(markdown)
        )
        sections.append(
            (
                heading_match.group("title").strip(),
                markdown[heading_match.start() : section_end].strip(),
            )
        )
    return sections


def _find_focused_section(
    *,
    spec: FocusedSectionSpec,
    available_sections: Sequence[tuple[str, str]],
) -> SourceSection:
    normalized_aliases = {_normalize_heading(alias) for alias in spec.heading_aliases}
    for heading, section_text in available_sections:
        if _normalize_heading(heading) in normalized_aliases:
            return SourceSection(
                document=spec.document,
                label=spec.label,
                heading=heading,
                text=section_text,
            )
    raise ValueError(
        f"Missing {spec.document}/{spec.label} benchmark section. "
        f"Expected one of: {', '.join(spec.heading_aliases)}"
    )


async def _build_section_report(
    *,
    source_section: SourceSection,
    chunk_result: ChunkResult,
    embeddings: EmbeddingAdapter,
) -> dict[str, object]:
    chunk_texts = [chunk.text for chunk in chunk_result.chunks]
    vectors = await asyncio.to_thread(embeddings.embed_documents, chunk_texts)
    semantic_metadata = _mapping(chunk_result.metadata.get("semantic_chunking"))
    usage = _mapping(semantic_metadata.get("usage"))
    fallback = _mapping(chunk_result.metadata.get("fallback"))
    validation = _mapping(chunk_result.metadata.get("validation"))

    return {
        "document": source_section.document,
        "section": source_section.label,
        "heading": source_section.heading,
        "source_valid": has_complete_source_line_coverage(
            source_text=source_section.text,
            chunk_texts=chunk_texts,
        ),
        "critical_content_preservation": critical_content_preservation(
            source_text=source_section.text,
            chunk_texts=chunk_texts,
        ),
        "validation": validation,
        "fallback": fallback,
        "latency_ms": _mapping(semantic_metadata.get("latency_ms")),
        "usage": usage,
        "embedding_vector_count": len(vectors),
        "chunk_count": len(chunk_result.chunks),
        "chunks": [
            {
                "index": chunk.index,
                "title": chunk.chunk_title,
                "tokens": chunk.token_estimate,
                "method": chunk.method,
                "text": chunk.text,
            }
            for chunk in chunk_result.chunks
        ],
    }


def has_complete_source_line_coverage(
    *,
    source_text: str,
    chunk_texts: Sequence[str],
) -> bool:
    source_lines = [_normalize_whitespace(line) for line in source_text.splitlines()]
    source_lines = [line for line in source_lines if line]
    output_lines = {
        _normalize_whitespace(line)
        for chunk_text in chunk_texts
        for line in chunk_text.splitlines()
        if _normalize_whitespace(line)
    }
    return all(source_line in output_lines for source_line in source_lines)


def critical_content_preservation(
    *,
    source_text: str,
    chunk_texts: Sequence[str],
) -> float:
    critical_lines = [
        _normalize_whitespace(line)
        for line in source_text.splitlines()
        if _is_critical_line(line)
    ]
    if not critical_lines:
        return 1.0

    output_text = "\n".join(_normalize_whitespace(text) for text in chunk_texts)
    preserved_line_count = sum(line in output_text for line in critical_lines)
    return round(preserved_line_count / len(critical_lines), 6)


def _is_critical_line(line: str) -> bool:
    clean_line = line.strip()
    return bool(
        DOSAGE_VALUE_PATTERN.search(clean_line)
        or clean_line.startswith(("- ", "* ", "+ ", "|"))
        or re.match(r"^\d+[.)]\s+", clean_line)
    )


def _summarize_sections(
    *,
    section_reports: Sequence[dict[str, object]],
) -> dict[str, object]:
    total_latency_ms = sum(
        float(_mapping(section["latency_ms"]).get("total", 0))
        for section in section_reports
    )
    reported_costs = [
        cost
        for section in section_reports
        if isinstance((cost := _mapping(section["usage"]).get("cost_usd")), int | float)
    ]
    fallback_count = sum(
        int(_mapping(section["fallback"]).get("count", 0))
        for section in section_reports
    )
    return {
        "section_count": len(section_reports),
        "all_sources_valid": all(
            section["source_valid"] is True for section in section_reports
        ),
        "average_critical_content_preservation": round(
            sum(
                _number(section["critical_content_preservation"])
                for section in section_reports
            )
            / len(section_reports),
            6,
        ),
        "average_latency_ms": round(total_latency_ms / len(section_reports), 2),
        "total_cost_usd": (
            round(sum(float(cost) for cost in reported_costs), 10)
            if reported_costs
            else None
        ),
        "fallback_count": fallback_count,
        "fallback_rate": round(fallback_count / len(section_reports), 6),
    }


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)
    return 0.0


def _normalize_heading(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return _normalize_whitespace(without_accents).upper().rstrip(":")


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _validate_inputs(*, pdf_paths: dict[str, Path], models: Sequence[str]) -> None:
    missing_paths = [str(path) for path in pdf_paths.values() if not path.is_file()]
    if missing_paths:
        raise ValueError("Missing benchmark PDFs: " + ", ".join(missing_paths))
    if len(models) != 2 or len(set(models)) != 2:
        raise ValueError("Benchmark requires two distinct model identifiers.")


async def async_main() -> None:
    arguments = build_argument_parser().parse_args()
    from dotenv import load_dotenv

    repository_env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(repository_env_path)

    from app.core.config import Settings

    settings = Settings(_env_file=repository_env_path)  # type: ignore[call-arg]
    report = await run_benchmark(
        settings=settings,
        pdf_paths={
            "dipirona": arguments.dipirona_pdf,
            "amoxicilina": arguments.amoxicilina_pdf,
        },
        models=(arguments.baseline_model, arguments.candidate_model),
        output_path=arguments.output,
    )
    print(
        json.dumps(
            {"output": str(arguments.output), "models": report["models"]},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(async_main())
