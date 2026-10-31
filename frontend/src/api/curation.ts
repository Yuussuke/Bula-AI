import type { BulaStatus } from "@/api/bulas";
import { ApiError, authFetch, requestJson } from "@/lib/api";
import type { AuthUser } from "@/store/auth";

export type ReviewStatus = "pending" | "approved" | "rejected" | "withdrawn";
export type CurationView = "public" | "mine" | "review";
export interface SharedBula {
  id: string;
  product_name: string;
  manufacturer: string | null;
  presentation: string | null;
  strength: string | null;
  source_url: string;
  source_description: string;
  review_status: ReviewStatus;
  ingestion_status: BulaStatus;
  is_available: boolean;
  version: number;
  submitted_at: string;
  sha256_checksum: string;
  content_size_bytes: number;
  error_message: string | null;
  ingestion_job_id: number | null;
  submitted_by_id: number;
  supersedes_bula_id: string | null;
}
export interface CurationEvent {
  id: string;
  actor_id: number | null;
  actor_role: string | null;
  operation_id: string | null;
  request_fingerprint: string | null;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  action: string;
  actor_name: string;
  reason: string;
  version: number;
  created_at: string;
}
export interface SharedDetail {
  document: SharedBula;
  events: CurationEvent[];
  submitted_by_name?: string | null;
}
export interface SharedPage {
  items: SharedBula[];
  total: number;
  limit: number;
  offset: number;
}
export interface CurationDecision {
  expected_version: number;
  reason: string;
  product_name?: string | null;
  manufacturer?: string | null;
  presentation?: string | null;
  strength?: string | null;
}

export interface SharedSubmissionInput {
  file: File;
  source_url: string;
  source_description: string;
  product_name: string;
  manufacturer: string | null;
}

export interface RoleAudit {
  id: string;
  user_id: number;
  actor_id: number | null;
  actor_name: string | null;
  actor_role: string | null;
  previous_role: AuthUser["role"];
  assigned_role: AuthUser["role"];
  reason: string;
  operation_id: string | null;
  request_fingerprint: string | null;
  created_at: string;
}

export function listSharedBulas(
  view: CurationView,
  status: ReviewStatus | "",
  query: string,
  page: number
): Promise<SharedPage> {
  const parameters = new URLSearchParams({
    view,
    query,
    limit: "20",
    offset: String((page - 1) * 20),
  });
  if (status) parameters.set("status", status);
  return requestJson<SharedPage>(`/api/v1/bulas/shared?${parameters}`, { method: "GET" });
}
export function getSharedBula(id: string): Promise<SharedDetail> {
  return requestJson<SharedDetail>(`/api/v1/bulas/shared/${id}`, { method: "GET" });
}
export function submitSharedBula(
  input: SharedSubmissionInput,
  operationId: string
): Promise<SharedBula> {
  const body = new FormData();
  body.set("file", input.file);
  body.set("source_url", input.source_url);
  body.set("source_description", input.source_description);
  body.set("product_name", input.product_name);
  if (input.manufacturer) body.set("manufacturer", input.manufacturer);
  return requestJson<SharedBula>("/api/v1/bulas/shared", {
    method: "POST",
    body,
    headers: { "Idempotency-Key": operationId },
  });
}
export function decideSharedBula(
  id: string,
  action: "approve" | "reject" | "withdraw" | "retry",
  payload: CurationDecision,
  operationId: string
): Promise<SharedBula> {
  return requestJson<SharedBula>(`/api/v1/bulas/shared/${id}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": operationId },
    body: JSON.stringify(payload),
  });
}
export async function getSharedPdf(id: string): Promise<Blob> {
  const response = await authFetch(`/api/v1/bulas/shared/${id}/pdf`, { method: "GET" });
  if (!response.ok)
    throw new ApiError(response.status, "Não foi possível carregar o PDF original.");
  return response.blob();
}
export function listCurationUsers(query: string, page: number): Promise<AuthUser[]> {
  const parameters = new URLSearchParams({ query, limit: "20", offset: String((page - 1) * 20) });
  return requestJson<AuthUser[]>(`/api/v1/auth/users?${parameters}`, { method: "GET" });
}
export function assignCurationRole(
  user: AuthUser,
  role: "user" | "contributor" | "reviewer",
  reason: string,
  operationId: string
): Promise<AuthUser> {
  return requestJson<AuthUser>(`/api/v1/auth/users/${user.id}/role`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", "Idempotency-Key": operationId },
    body: JSON.stringify({ role, expected_role: user.role, reason }),
  });
}

export function getCurationRoleHistory(userId: number, page: number): Promise<RoleAudit[]> {
  const parameters = new URLSearchParams({ limit: "20", offset: String((page - 1) * 20) });
  return requestJson<RoleAudit[]>(`/api/v1/auth/users/${userId}/role-history?${parameters}`, {
    method: "GET",
  });
}
