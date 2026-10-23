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
the executed retrieval mode; the full mode selector (#51) remains separate.
No dependencies, datasets, provider prompts or experimental results change.
