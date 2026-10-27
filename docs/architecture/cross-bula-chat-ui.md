# General-chat interface

The authenticated `/chat` page reuses the existing chat components. The catalog
links to it; `/bulas/:id/chat` remains document-scoped. It requires the backend's
`POST /chat/ask`, explicit session `scope` and server-side history filters.
Deploy the backend migration/API first. General chat searches published system
leaflets; shared leaflets remain blocked. BGE is configured by the backend,
independently of these controls; see `rrfb-bge-runtime.md`.

Query keys include document/general context. Loaded session scope and document
identity must match the page before sending; missing scope on old sessions is
treated as `bula`, never inferred as general from a null document ID. Transient
messages and completed requests retain their originating context.

Sources show original numbering, medication, available presentation/manufacturer
and canonical HTTP(S) links. Individual/grouped citations navigate to the same
source order. These links do not certify semantic support. Message badges show
the executed retrieval mode, independently of the next request's selection.
No dependencies, datasets, provider prompts or experimental results change.

## Retrieval mode selection (#51)

Both chat routes offer Semântico (`dense`), Palavras-chave (`bm25`) and Híbrido
(`hybrid`), with short explanations. New conversations default to hybrid.
Every question explicitly sends the selected mode; the selector is disabled
during a request. Reopening a session restores the last assistant message's
stored mode, using the existing history contract without a new database field.
An unsent selection is local state, not a persisted session preference.

Unknown returned modes remain unidentified in history and produce a warning;
new requests default to hybrid. A field-specific HTTP 422 for `body.mode` resets
the next selection to hybrid and preserves the question for manual resubmission.
There is no automatic retry. Other validation errors do not change the mode,
and a late failure from another conversation cannot reset the current selection.

## Conversation workspace

Chat fills the available viewport. Identity and search-mode controls live in the
sidebar/mobile drawer; each answer still shows its executed mode. The input grows
from one line to 144 px and retains a visible medical-information notice. Editable
general-chat suggestions use `[medicamento]`; selecting one never submits it.

Reading older messages suspends auto-follow, with an explicit latest-message
action. Numbered/grouped citations open a source panel without rewriting stored
answers or renumbering references. Document identity and original links remain
attached; closing the panel restores focus to the citation. Catalog return links
retain filters/page. Retrieval, authorization and experimental artifacts are unchanged.
