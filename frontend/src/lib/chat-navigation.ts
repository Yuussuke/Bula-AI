import type { ChatSessionResponse } from "@/api/chat";
import { catalogParameters } from "@/lib/catalog-scope";

export function getChatSessionPath(session: ChatSessionResponse): string | null {
  const scope = session.scope ?? "bula";
  if (scope === "bula" && session.bula_id === null) return null;
  const parameters = catalogParameters(
    scope === "cross_bula" ? (session.catalog_scope ?? "all") : "all"
  );
  parameters.set("session", session.id);
  const path = scope === "cross_bula" ? "/chat" : `/bulas/${session.bula_id}/chat`;
  return `${path}?${parameters.toString()}`;
}
