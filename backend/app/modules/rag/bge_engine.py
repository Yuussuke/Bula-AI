"""Pinned BGE assets, local CUDA/FP16 inference, without network/model fallback."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from time import monotonic
from typing import Any

import structlog

from app.modules.rag.reranker import RerankerError

BGE_MODEL_ID = "BAAI/bge-reranker-v2-m3"
BGE_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
BGE_MAX_PAIR_TOKENS = 8192
logger = structlog.get_logger(__name__)


class BGEEngine:
    def __init__(self, model_path: Path) -> None:
        self._verify_assets(model_path)
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise RerankerError(
                "Install the backend reranker extra to enable BGE."
            ) from exc
        if not torch.cuda.is_available():
            raise RerankerError("BGE requires CUDA; CPU fallback is disabled.")
        torch.manual_seed(20261014)
        torch.set_num_threads(4)
        torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.cuda.set_per_process_memory_fraction(0.85, 0)
        self._torch = torch
        self._tokenizer: Any = AutoTokenizer.from_pretrained(
            str(model_path),
            local_files_only=True,
            trust_remote_code=False,
            use_fast=True,
        )
        self._model: Any = (
            AutoModelForSequenceClassification.from_pretrained(
                str(model_path),
                dtype=torch.float16,
                attn_implementation="sdpa",
                local_files_only=True,
                trust_remote_code=False,
                use_safetensors=True,
            )
            .to("cuda:0")
            .eval()
        )
        logger.info(
            "rag_reranker_loaded",
            model=BGE_MODEL_ID,
            revision=BGE_REVISION,
            torch=torch.__version__,
            device=torch.cuda.get_device_name(0),
            dtype="float16",
            batch_size=1,
            max_pair_tokens=BGE_MAX_PAIR_TOKENS,
        )

    def _verify_assets(self, model_path: Path) -> None:
        manifest = json.loads(
            Path(__file__).with_name("bge_assets.json").read_text(encoding="utf-8")
        )
        for filename, expected_hash in manifest.items():
            path = model_path / filename
            try:
                with path.open("rb") as source:
                    digest = hashlib.file_digest(source, "sha256").hexdigest()
            except OSError as exc:
                raise RerankerError(f"BGE asset unavailable: {filename}.") from exc
            if digest != expected_hash:
                raise RerankerError(f"BGE asset hash mismatch: {filename}.")

    def score(self, query: str, passages: list[str], *, deadline: float) -> list[float]:
        encoded = self._tokenizer(
            [query] * len(passages),
            passages,
            padding=False,
            truncation=False,
            return_attention_mask=True,
        )
        if any(
            not row or len(row) > BGE_MAX_PAIR_TOKENS for row in encoded["input_ids"]
        ):
            raise RerankerError("BGE pair exceeds 8192 tokens; truncation is disabled.")
        scores = []
        for index in range(len(passages)):
            if monotonic() >= deadline:
                raise RerankerError("BGE deadline exceeded.")
            row = {key: values[index] for key, values in encoded.items()}
            tensors = self._tokenizer.pad([row], padding=True, return_tensors="pt").to(
                "cuda:0"
            )
            with self._torch.inference_mode():
                logits = self._model(**tensors).logits.float().cpu().flatten().tolist()
            if len(logits) != 1:
                raise RerankerError("BGE must return one raw logit per pair.")
            scores.append(float(logits[0]))
        return scores
