import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getBulaStatus,
  getSystemBula,
  listSystemBulas,
  listUserBulas,
  type SystemBulaResponse,
  uploadBula,
  type UserBulaResponse,
} from "@/api/bulas";
import { queryClient } from "@/lib/queryClient";
import { useAuthStore } from "@/store/auth";

const API_BASE_URL = "http://localhost:8000";
const BULA_ID = "11111111-1111-4111-8111-111111111111";

function buildUserBula(overrides: Partial<UserBulaResponse> = {}): UserBulaResponse {
  return {
    id: BULA_ID,
    user_id: 4,
    drug_name: "Dipirona",
    alias: null,
    manufacturer: "Sanofi Medley",
    file_url: null,
    file_address: "stored_objects/dipirona",
    qdrant_collection: null,
    status: "pending",
    error_message: null,
    corpus: "private",
    created_at: "2026-09-07T12:00:00Z",
    updated_at: "2026-09-07T12:00:00Z",
    ...overrides,
  };
}

describe("system bula API", () => {
  beforeEach(() => {
    useAuthStore.getState().setAuth({
      accessToken: "access-token",
      user: {
        id: 4,
        email: "user@bulaai.local",
        name: "Test User",
        role: "user",
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    useAuthStore.getState().clearAuth();
    queryClient.clear();
  });

  it("lists the authenticated system catalog with bounded pagination", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(listSystemBulas({ limit: 50, offset: 10 })).resolves.toEqual([]);

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/bulas/system?limit=50&offset=10`,
      expect.objectContaining({ method: "GET", credentials: "include" })
    );
    const requestHeaders = new Headers(fetchMock.mock.calls[0][1]?.headers);
    expect(requestHeaders.get("Authorization")).toBe("Bearer access-token");
  });

  it("retrieves the published system bula detail", async () => {
    const systemBula: SystemBulaResponse = {
      id: BULA_ID,
      target_id: "amoxicilina-clavulanato-500mg-125mg-comprimido-ems",
      product_name: "AMOXICILINA + CLAVULANATO DE POTASSIO",
      active_ingredient: "amoxicilina + clavulanato de potassio",
      strength: "500 mg + 125 mg",
      pharmaceutical_form: "comprimido revestido",
      presentation: "embalagem com 12 unidades",
      audience: "patient",
      manufacturer: "EMS S/A",
      company_tax_id: "57507378000365",
      anvisa_product_id: 124891,
      registration_number: "102350532",
      process_number: "253510242290107",
      expedition_number: "0186508263",
      transaction_number: "2551962026",
      source_record_id: "35934920",
      canonical_source_url: "https://consultas.anvisa.gov.br/api/consulta/bulario",
      source_published_at: "2026-02-25T17:20:51Z",
      source_updated_at: "2026-08-26T03:00:00Z",
      sha256_checksum: "ffd3780e4895c67b9bf1986127e4a205265245f865b6b0123843400582689d41",
      content_size_bytes: 231137,
      ingestion_status: "ready",
      publication_state: "published",
      reviewed_by: "Reviewer",
      reviewed_at: "2026-09-02T02:50:18Z",
      published_at: "2026-09-02T02:50:35Z",
    };
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(systemBula), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getSystemBula(BULA_ID)).resolves.toEqual(systemBula);

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/bulas/system/${BULA_ID}`,
      expect.objectContaining({ method: "GET", credentials: "include" })
    );
  });

  it("retrieves ingestion status for a user-owned upload", async () => {
    const statusResponse = {
      id: BULA_ID,
      drug_name: "Dipirona",
      alias: null,
      manufacturer: "Sanofi Medley",
      status: "processing" as const,
      error_message: null,
    };
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(statusResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getBulaStatus(BULA_ID)).resolves.toEqual(statusResponse);

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/bulas/${BULA_ID}/status`,
      expect.objectContaining({ method: "GET", credentials: "include" })
    );
  });

  it("lists user-owned bulas", async () => {
    const userBulas = [buildUserBula()];
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(userBulas), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(listUserBulas()).resolves.toEqual(userBulas);

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/bulas/`,
      expect.objectContaining({ method: "GET", credentials: "include" })
    );
  });

  it("uploads a PDF as multipart form data without overriding its content type", async () => {
    const uploadedBula = buildUserBula();
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(uploadedBula), {
        status: 202,
        headers: { "Content-Type": "application/json" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);
    const pdfFile = new File(["%PDF-1.7"], "dipirona.pdf", {
      type: "application/pdf",
    });

    await expect(
      uploadBula({
        alias: "  Dipirona da minha mãe  ",
        file: pdfFile,
      })
    ).resolves.toEqual(uploadedBula);

    const requestInit = fetchMock.mock.calls[0][1];
    const requestBody = requestInit?.body;
    expect(requestBody).toBeInstanceOf(FormData);
    expect((requestBody as FormData).get("alias")).toBe("Dipirona da minha mãe");
    expect((requestBody as FormData).has("drug_name")).toBe(false);
    expect((requestBody as FormData).has("manufacturer")).toBe(false);
    expect((requestBody as FormData).get("file")).toBe(pdfFile);
    expect(new Headers(requestInit?.headers).has("Content-Type")).toBe(false);
  });
});
