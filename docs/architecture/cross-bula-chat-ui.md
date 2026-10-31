# General-chat interface

The authenticated `/chat` page reuses the existing chat components. The catalog
links to it; `/bulas/:id/chat` remains document-scoped. It requires the backend's
`POST /chat/ask`, explicit session `scope` and server-side history filters.
Deploy the backend migration/API first. General chat offers General, ANVISA and
Shared catalogs; only eligible public sources are available. The catalog boundary
is saved per conversation and restored from the server. Changing it starts a new
conversation, preserving the draft and existing history. BGE is configured by the backend,
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

Chat fills the available viewport. On compact screens, catalog and search-mode
controls sit in the header, outside the history drawer. Desktop controls use a
small wrapping row, or icons when the sidebar is collapsed; labels are not clipped.
Each answer still shows its executed mode. The input grows
from one line to 144 px and retains a visible medical-information notice. Editable
general-chat suggestions use `[medicamento]`; selecting one never submits it.

Reading older messages suspends auto-follow, with an explicit latest-message
action. Numbered/grouped citations open a source panel without rewriting stored
answers or renumbering references. Document identity and original links remain
attached; closing the panel restores focus to the citation. Catalog return links
retain filters/page. Retrieval, authorization and experimental artifacts are unchanged.

The shared workspace sidebar is available throughout the site. Its rail contains
the logo and navigation shortcuts; the adjacent panel contains conversations.
Collapse by button, keyboard or dragging the edge. A fixed inner panel width
avoids reflowing its text during the outer width transition. Layout state is shared
across routes through Zustand, independently of chat/authentication data.
Icon hints also open on keyboard focus and respect reduced-motion preferences.

Conversation menus support renaming (1–50 trimmed characters) and confirmed
deletion. Authenticated `PATCH /chat/sessions/{id}` accepts `{title}`; `DELETE`
returns `{session_id}`. Both restrict the database mutation to the owner and use
404 for missing/inaccessible sessions. Deletion cascades to that session's
messages, preserving PDFs and other conversations. Failed mutations keep the
dialog/draft for manual retry. Deleting the active conversation opens a new one
within its existing catalog boundary; a turn in progress disables its menu.

The same PATCH accepts `{is_pinned: true|false}`. Pins belong to the session's
owner and persist across reloads without changing messages, source boundaries
or last-activity timestamps. The optional `is_pinned` list filter is applied
before pagination. A separate paginated Pinned group appears above Recents;
pinned conversations are excluded from both recent scope groups. Unpinning
restores a conversation to its original scope. Apply Alembic migration
`e610a130b004` before starting this version; existing sessions default to unpinned.

The shared rail includes an animated light/dark shortcut, also available in the
compact navigation drawers. The existing next-themes provider follows the OS
initially and stores only an explicit theme preference under `bula-ai-theme`.
Dark colors reuse semantic tokens; warnings and status badges have dedicated
dark variants. Icon transitions respect reduced-motion preferences.
