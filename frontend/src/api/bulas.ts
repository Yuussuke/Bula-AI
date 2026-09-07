import { requestJson } from "@/lib/api";

export type BulaStatus = "pending" | "processing" | "ready" | "failed" | "error";
export type SystemBulaPublicationState =
  | "staged"
  | "vetted"
  | "published"
  | "withdrawn"
  | "rejected";
export type BulaAudience = "patient" | "professional";
export type BulaCorpus = "private" | "system" | "shared";

export interface UserBulaResponse {
  id: string;
  user_id: number;
  drug_name: string;
  alias: string | null;
  manufacturer: string | null;
  file_url: string | null;
  file_address: string | null;
  qdrant_collection: string | null;
  status: BulaStatus;
  error_message: string | null;
  corpus: BulaCorpus;
  created_at: string;
  updated_at: string;
}

export interface UploadBulaRequest {
  alias?: string;
  file: File;
}

export interface SystemBulaResponse {
  id: string;
  target_id: string;
  product_name: string;
  active_ingredient: string;
  strength: string;
  pharmaceutical_form: string;
  presentation: string;
  audience: BulaAudience;
  manufacturer: string;
  company_tax_id: string;
  anvisa_product_id: number;
  registration_number: string;
  process_number: string;
  expedition_number: string;
  transaction_number: string;
  source_record_id: string;
  canonical_source_url: string;
  source_published_at: string;
  source_updated_at: string | null;
  sha256_checksum: string;
  content_size_bytes: number;
  ingestion_status: BulaStatus;
  publication_state: SystemBulaPublicationState;
  reviewed_by: string | null;
  reviewed_at: string | null;
  published_at: string | null;
}

export interface BulaStatusResponse {
  id: string;
  drug_name: string;
  alias: string | null;
  manufacturer: string | null;
  status: BulaStatus;
  error_message: string | null;
}

export interface QueryableBulaResponse {
  id: string;
  product_name: string;
  active_ingredient: string | null;
  strength: string | null;
  manufacturer: string | null;
  corpus: BulaCorpus;
  ingestion_status: BulaStatus;
}

export interface ListSystemBulasOptions {
  limit?: number;
  offset?: number;
}

export async function listSystemBulas({
  limit = 100,
  offset = 0,
}: ListSystemBulasOptions = {}): Promise<SystemBulaResponse[]> {
  const searchParams = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  return requestJson<SystemBulaResponse[]>(`/api/v1/bulas/system?${searchParams.toString()}`, {
    method: "GET",
  });
}

export async function getSystemBula(bulaId: string): Promise<SystemBulaResponse> {
  return requestJson<SystemBulaResponse>(`/api/v1/bulas/system/${bulaId}`, {
    method: "GET",
  });
}

export async function getQueryableBula(bulaId: string): Promise<QueryableBulaResponse> {
  return requestJson<QueryableBulaResponse>(`/api/v1/bulas/${bulaId}`, {
    method: "GET",
  });
}

export async function getBulaStatus(bulaId: string): Promise<BulaStatusResponse> {
  return requestJson<BulaStatusResponse>(`/api/v1/bulas/${bulaId}/status`, {
    method: "GET",
  });
}

export async function listUserBulas(): Promise<UserBulaResponse[]> {
  return requestJson<UserBulaResponse[]>("/api/v1/bulas/", {
    method: "GET",
  });
}

export async function uploadBula({ alias, file }: UploadBulaRequest): Promise<UserBulaResponse> {
  const formData = new FormData();
  if (alias?.trim()) {
    formData.set("alias", alias.trim());
  }
  formData.set("file", file);

  return requestJson<UserBulaResponse>("/api/v1/bulas/upload", {
    method: "POST",
    body: formData,
  });
}
