# RAG parser golden fixtures

These PDFs and Markdown references protect the PDF-to-Markdown parser against
gross structural regressions. The BLEU and token-F1 thresholds in the golden
test are intentionally relaxed baseline guards, not final quality targets.

Refresh references only after reviewing an intentional parser change:

```bash
cd backend
uv run python scripts/update_parser_goldens.py
uv run pytest -v tests/integration/rag/test_bula_parser_goldens.py
```
