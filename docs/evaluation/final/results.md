# Archived final-evaluation results

These are descriptive results of 120 paired needs, not population estimates,
clinical certification or evidence of statistically significant superiority.
Original outputs and both evaluators' numerical grades remain unchanged.

## Retrieval

There are 960 scored ranking records (120 × two scenarios × four arms).
BM25/dense are captured candidate branches of the common experiment, not new
standalone factory runs. Safety supplements are excluded from these rankings.
Recall means macro chunk recall, not answer accuracy or required-answer coverage.

### Primary: 85 full-support needs per scenario

| Scenario | Arm | Recall@10 | MRR@10 | At least one gold |
| --- | --- | ---: | ---: | ---: |
| Scoped | BM25 | 0.8413 | 0.5790 | 78/85 |
| Scoped | Dense | 0.9396 | 0.6246 | 83/85 |
| Scoped | RRF-B | 0.9168 | 0.6609 | 82/85 |
| Scoped | RRF-B + BGE | 0.9300 | 0.6802 | 82/85 |
| Cross | BM25 | 0.6864 | 0.4752 | 67/85 |
| Cross | Dense | 0.8182 | 0.5985 | 74/85 |
| Cross | RRF-B | 0.8417 | 0.5918 | 76/85 |
| Cross | RRF-B + BGE | 0.9013 | 0.6866 | 80/85 |

### Secondary: 19 partial-support needs per scenario

| Scenario | Arm | Recall@10 | MRR@10 | At least one gold |
| --- | --- | ---: | ---: | ---: |
| Scoped | BM25 | 0.5877 | 0.5066 | 15/19 |
| Scoped | Dense | 0.8026 | 0.5716 | 19/19 |
| Scoped | RRF-B | 0.8158 | 0.4568 | 19/19 |
| Scoped | RRF-B + BGE | 0.8509 | 0.6203 | 19/19 |
| Cross | BM25 | 0.4342 | 0.3467 | 11/19 |
| Cross | Dense | 0.6316 | 0.5930 | 16/19 |
| Cross | RRF-B | 0.5921 | 0.5436 | 16/19 |
| Cross | RRF-B + BGE | 0.7368 | 0.5255 | 17/19 |

Partial metrics concern the documented portion, not complete answerability.
The source-conflict case is separate; 15 unsupported needs have N/A Recall/MRR.
`Q039` remains in the primary denominator with zero, not a fabricated chunk ID.
Qrels do not prove exhaustive annotation of every equivalent source paraphrase.
Dense has the highest scoped primary recall; BGE has the highest primary MRR
in both scenarios and primary cross recall. No arm dominates every reported metric.

## Original answer assessments

All 240 outputs were assessed by the author and Gemini 2.5 Pro separately.
Scores are ordinal 1–4; N/A is excluded independently per dimension.

| Dimension | Human n / N/A | Human mean | Gemini n / N/A | Gemini mean |
| --- | ---: | ---: | ---: | ---: |
| Documentary fidelity | 223 / 17 | 3.964 | 223 / 17 | 3.677 |
| Indispensable information | 223 / 17 | 3.960 | 224 / 16 | 3.683 |
| Relevance | 222 / 18 | 3.968 | 223 / 17 | 3.969 |
| Clarity | 223 / 17 | 4.000 | 233 / 7 | 4.000 |
| Safety | 223 / 17 | 3.982 | 230 / 10 | 3.713 |

| Dimension | Applicable pairs | Exact agreement | Quadratic weighted kappa | N/A mismatches |
| --- | ---: | ---: | ---: | ---: |
| Documentary fidelity | 222 | 81.53% | 0.167 | 2 |
| Indispensable information | 222 | 75.68% | 0.125 | 3 |
| Relevance | 221 | 97.29% | 0.663 | 3 |
| Clarity | 223 | 100.00% | Undefined | 10 |
| Safety | 223 | 81.17% | 0.144 | 7 |

Grades concentrate at 4; kappa must be read with exact agreement and applicability
mismatches. Clarity's zero expected disagreement makes kappa undefined, not zero.
Means and high-grade rates are not an overall correctness or clinical-safety rate.

Human classifications: 203 substantive, 20 grounded-partial, 16 full abstentions,
one technical failure. Gemini: 206, 17, 16 and one respectively. On the 16 full
abstentions, human adequacy grades were 14×4, 1×2, 1×1; Gemini's were 5×4, 3×2,
8×1. These are separate assessments, not an adjudicated false-abstention rate.
Gemini flagged 28 unsupported claims, 17 citation problems and 19 safety risks;
human flags were zero, two and zero. Flags overlap and are not confirmed defects.

## Closed divergence review

The original rule identified 74 disagreements: 26 with a ≥2-point gap, 50 flag
differences, 15 classification differences and 27 abstention-flag differences
(overlapping groups). All 74 received an explicit author adjudication:

| Interpretation preferred | Cases |
| --- | ---: |
| Human | 50 |
| Gemini | 19 |
| Both assessments problematic | 4 |
| Inconclusive | 1 |

`Q107-scoped` remains inconclusive; closing the round does not resolve it. The
`Q010-scoped` unsaved draft is outside the registered cohort. All 19 judge-flagged
safety cases were reviewed, not automatically certified resolved. Preserve the
247 initial human events and 81 adjudication events. Categorical preference does
not endorse every grade or establish a completely correct answer. No replacement
grades, post-adjudication accuracy or revised agreement statistic are inferred.

## Operations and limitations

- 239/240 technically accepted outputs; `Q018-scoped` retains its original
  `missing_source_citation` rejection and N/A quality scores. Its optional draft
  is excluded, not substituted. Full diagnostic abstentions: seven scoped/nine cross.
- 464 observed Sabiá-4 calls: 240 selections and 224 generations; no automatic
  retries/fallback. Gemini produced 240 structured judgments with no technical
  failures, retries or fallback. Technical validity does not establish fidelity.
- Cached-context selection/generation/validation: P50 2.29 s, P95 25.15 s,
  including pacing and excluding retrieval/reranking. Not live end-to-end latency.
- Approximate Flesch PT-BR on 223 informative outputs: mean 50.34, median 50.04;
  Pyphen 0.17.2 hyphenation is a syllable approximation, not patient-comprehension
  validation. No RAGAS score or external professional evaluation is claimed.
- The author is not an independent blinded specialist evaluator. Adjudication
  saw both judgments; Gemini received saved references/context, not complete PDFs.
  Some source equivalences remain unannotated; the sample is purposive and its
  PDFs were previously used in development. These limitations constrain inference.

The [inventory](provenance.json) binds the untouched source summaries and closure.
The [protocol](README.md) and [custody instructions](reproduction.md) define the
denominators and reproduction boundary. No new metrics/run or tuning was performed
for this publication; the original archive retains per-case and corpus strata.
