import type { SharedBula } from "@/api/curation";

export function isSharedBulaProcessing(document: SharedBula): boolean {
  return (
    document.review_status === "approved" &&
    (document.ingestion_status === "pending" || document.ingestion_status === "processing")
  );
}
