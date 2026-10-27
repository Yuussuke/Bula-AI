# Catalog metadata and navigation

Verified imports may preserve unknown manufacturer/acquisition fields as null.
This does not relax the downloader manifest or publication/readiness, PDF checksum,
stored-size and canonical-source checks. Missing provenance is never fabricated.
Complete strength labels use text to preserve multiple presentations. Alembic
revisions `d510a102b001` and `d510a102b002` apply these changes; downgrades reject
unresolved nulls or overlong values instead of inventing/truncating metadata.
No documents are imported or republished by these migrations.
