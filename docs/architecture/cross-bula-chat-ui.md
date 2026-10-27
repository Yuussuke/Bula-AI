# General-chat interface

The authenticated `/chat` page reuses the existing chat components. The catalog
links to it; `/bulas/:id/chat` remains document-scoped. It requires the backend's
`POST /chat/ask`, explicit session `scope` and server-side history filters.
Deploy the backend migration/API first. Shared leaflets and BGE are not enabled
by this UI; general chat initially searches published system leaflets only.

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
