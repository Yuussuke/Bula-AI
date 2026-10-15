# BGE concurrency: measured trade-offs

Separate operational prototype, not answer-quality evaluation or production
certification. There were 188 trials and 1,785 requests, plus 144 calibration
requests excluded from throughput. No paid APIs, new embeddings, LLMs, ingestion
or index writes. The [summary](summary.json) identifies the immutable archive.

## Setup and findings

Windows, Python 3.12.13, PyTorch 2.8.0+cu128, Transformers 4.57.1;
RTX 3050 Laptop GPU, approximately 4 GiB VRAM. One resident CUDA FP16 model,
four CPU threads, one interop thread, FIFO queue capacity 16, request deadline
15 seconds; sequential and microbatched inference with batch sizes 2/4.

Workloads: 36 development scoped questions and 12 historical cross-bula questions,
six per corpus. Final24 results were excluded. Cross searched each corresponding
50-PDF universe without a target filter. Workloads differ between scenarios;
they do not isolate the causal effect of scoped versus cross retrieval.

| Sequential confirmation | Arrival rate | Window | Successes | P95 |
|---|---:|---:|---:|---:|
| Scoped | 1 request/s | 60 s | 60/60 | 1,135 ms |
| Cross-bula | 0.5 requests/s | 60 s | 30/30 | 1,048 ms |

Batch 2 confirmed the same respective rates for 90 seconds, not higher sustained
capacity. These finite-window confirmations are not hardware maximums or full
HTTP/LLM throughput. Short pilots can underestimate sustainable capacity.

- Across BGE load trials, saturation caused 38 overload rejections, 27 execution
  timeouts and nine queue timeouts. No OOM/CUDA errors were observed; this does
  not mean every request succeeded. RRF-only burst20 also had four rejections.
- Sampled peaks: process RSS 4.19 GiB, GPU-driver usage 1,902 MiB; these are
  different from PyTorch allocated/reserved memory, not additive measurements.
- Batch 2 improved matched burst throughput by about 5% scoped and 20% cross;
  batch 4 did not consistently improve it. No higher confirmed rate resulted.
- Calibration changed Top-10 order in 4/48 batch-2 and 3/48 batch-4 requests,
  but never Top-10 membership. Numerical equivalence must not be assumed.
- The configured 5 ms batch-formation window was a soft target, not an observed
  maximum. P95 values are exploratory; P99 was withheld for small per-trial samples.

## Decision boundary

The author's qualitative preference for BGE comes from the paired answer reviews,
not this load test. RRF-B alone is cheaper computationally; BGE adds GPU/RAM demand
and queueing risk. A minimal future integration needs a resident model, bounded
inference, explicit overload handling and preserved authorization/provenance.
These results do not justify adding microbatching to production now, loading a
model per request, or silently falling back to another retrieval configuration.

The native prototype does not establish compatibility with the Python 3.14
backend container. Mixed system/shared/multi-owner access, uncached query
embedding, provider quotas and full HTTP latency were not certified here.
Use the archive's effective `presentation-v2`; the earlier presentation overstated
the 5 ms target. Original measurements and superseded presentations are preserved.
