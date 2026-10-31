import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLayoutEffect, useRef, useState } from "react";

import {
  askBulaQuestion,
  askCrossBulaQuestion,
  type AskResponse,
  type ChatContext,
  type ChatSessionResponse,
  continueChatSession,
  getChatSession,
  type RetrievalMode,
} from "@/api/chat";
import type { ChatTimeline, ChatTimelineMessage } from "@/components/chat/types";
import { ApiError } from "@/lib/api";
import { type CatalogScope, isCatalogScope } from "@/lib/catalog-scope";
import { isRetrievalMode } from "@/lib/retrieval-mode";

interface SendQuestionVariables {
  catalogScope: CatalogScope;
  question: string;
  sessionId: string | null;
  optimisticUserMessageId: string;
  context: ChatContext;
  contextKey: string;
  conversationRevision: number;
  mode: RetrievalMode;
}

interface TransientChatMessage extends ChatTimelineMessage {
  conversationKey: string;
}

interface UseChatSessionOptions {
  catalogScope?: CatalogScope;
  context: ChatContext;
  sessionId: string | null;
  onSessionCreated: (sessionId: string) => void;
}

interface UseChatSessionResult {
  catalogScope: CatalogScope;
  messages: ChatTimelineMessage[];
  loadedBulaId: string | null;
  hasContextMismatch: boolean;
  isLoading: boolean;
  isSending: boolean;
  loadError: Error | null;
  sendError: Error | null;
  sendQuestion: (question: string) => Promise<boolean | null>;
  invalidatePendingConversation: () => void;
  mode: RetrievalMode;
  setMode: (mode: RetrievalMode) => void;
  modeWarning: string | null;
}

class ChatContextMismatchError extends Error {}

function buildSessionQueryKey(
  contextKey: string,
  sessionId: string
): readonly ["chat-session", string, string] {
  return ["chat-session", contextKey, sessionId] as const;
}

function mapSessionToTimeline(session: ChatSessionResponse): ChatTimeline {
  if (session.catalog_scope != null && !isCatalogScope(session.catalog_scope)) {
    throw new Error("O servidor informou um catálogo inválido para esta conversa.");
  }
  const lastAssistantMode = session.messages.findLast(
    (message) => message.role === "assistant"
  )?.retrieval_mode;
  return {
    catalogScope: session.catalog_scope ?? "all",
    sessionId: session.id,
    bulaId: session.bula_id,
    scope: session.scope ?? "bula",
    hasInvalidMode: lastAssistantMode != null && !isRetrievalMode(lastAssistantMode),
    messages: session.messages.map((message) => ({
      id: message.id,
      role: message.role,
      content: message.content,
      sourceChunks: message.source_chunks ?? [],
      retrievalMode: isRetrievalMode(message.retrieval_mode) ? message.retrieval_mode : null,
    })),
  };
}

function buildTurnMessages(
  question: string,
  response: AskResponse,
  userMessageId: string
): [ChatTimelineMessage, ChatTimelineMessage] {
  return [
    {
      id: userMessageId,
      role: "user",
      content: question,
      sourceChunks: [],
    },
    {
      id: `local-assistant-${crypto.randomUUID()}`,
      role: "assistant",
      content: response.answer,
      sourceChunks: response.source_chunks,
      retrievalMode: isRetrievalMode(response.retrieval_mode) ? response.retrieval_mode : null,
    },
  ];
}

function buildConversationKey(contextKey: string, sessionId: string | null): string {
  return `${contextKey}:${sessionId ?? "new"}`;
}

export function useChatSession({
  catalogScope = "all",
  context,
  sessionId,
  onSessionCreated,
}: UseChatSessionOptions): UseChatSessionResult {
  const queryClient = useQueryClient();
  const isSendInFlightRef = useRef(false);
  const conversationRevisionRef = useRef(0);
  const isMountedRef = useRef(false);
  const [preference, setPreference] = useState<{
    conversationKey: string;
    mode: RetrievalMode;
  } | null>(null);
  const [rejectedModeConversation, setRejectedModeConversation] = useState<string | null>(null);
  const [transientUserMessage, setTransientUserMessage] = useState<TransientChatMessage | null>(
    null
  );
  const bulaId = context.scope === "bula" ? context.bulaId : null;
  const contextKey = `${context.scope}:${bulaId ?? catalogScope}`;
  const conversationKey = buildConversationKey(contextKey, sessionId);
  useLayoutEffect(() => {
    isMountedRef.current = true;
    conversationRevisionRef.current += 1;
    return () => {
      isMountedRef.current = false;
      conversationRevisionRef.current += 1;
    };
  }, [conversationKey]);

  const isCurrentRequest = (revision: number): boolean =>
    isMountedRef.current && conversationRevisionRef.current === revision;
  const sessionQuery = useQuery({
    queryKey: sessionId
      ? buildSessionQueryKey(contextKey, sessionId)
      : ["chat-session", contextKey, "new"],
    queryFn: async (): Promise<ChatTimeline> => {
      if (!sessionId) {
        throw new Error("A session identifier is required to load chat history.");
      }

      const session = mapSessionToTimeline(await getChatSession(sessionId));
      if (session.scope !== context.scope || session.bulaId !== bulaId) {
        throw new ChatContextMismatchError("A conversa pertence a outro contexto.");
      }
      return session;
    },
    enabled: Boolean(sessionId),
    staleTime: Number.POSITIVE_INFINITY,
  });

  const sendMutation = useMutation({
    mutationFn: async ({
      question,
      sessionId: existingSessionId,
      context: questionContext,
      mode,
      catalogScope: requestedCatalogScope,
    }: SendQuestionVariables) => {
      if (existingSessionId) {
        return continueChatSession(existingSessionId, { question, mode });
      }

      if (questionContext.scope === "cross_bula")
        return askCrossBulaQuestion({ question, mode, catalog_scope: requestedCatalogScope });
      return askBulaQuestion(questionContext.bulaId, { question, mode });
    },
    onSuccess: (response, variables) => {
      const nextSessionId = response.session_id;
      const nextQueryKey = buildSessionQueryKey(variables.contextKey, nextSessionId);
      const existingTimeline = variables.sessionId
        ? queryClient.getQueryData<ChatTimeline>(
            buildSessionQueryKey(variables.contextKey, variables.sessionId)
          )
        : undefined;
      const newMessages = buildTurnMessages(
        variables.question,
        response,
        variables.optimisticUserMessageId
      );

      queryClient.setQueryData<ChatTimeline>(nextQueryKey, {
        catalogScope:
          response.catalog_scope ?? existingTimeline?.catalogScope ?? variables.catalogScope,
        sessionId: nextSessionId,
        bulaId: variables.context.scope === "bula" ? variables.context.bulaId : null,
        scope: variables.context.scope,
        hasInvalidMode: !isRetrievalMode(response.retrieval_mode),
        messages: [...(existingTimeline?.messages ?? []), ...newMessages],
      });
      void queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });

      if (!variables.sessionId && isCurrentRequest(variables.conversationRevision)) {
        onSessionCreated(nextSessionId);
      }
    },
    retry: false,
  });

  const lastMode = sessionQuery.data?.messages.findLast(
    (message) => message.role === "assistant"
  )?.retrievalMode;
  const hasInvalidMode = sessionQuery.data?.hasInvalidMode ?? false;
  const restoredMode = !hasInvalidMode && isRetrievalMode(lastMode) ? lastMode : "hybrid";
  const mode = preference?.conversationKey === conversationKey ? preference.mode : restoredMode;

  const sendQuestion = async (question: string): Promise<boolean | null> => {
    if (sessionId && (!sessionQuery.data || sessionQuery.error)) return false;
    if (isSendInFlightRef.current) {
      return false;
    }

    isSendInFlightRef.current = true;
    const conversationRevision = conversationRevisionRef.current;
    const optimisticUserMessage: TransientChatMessage = {
      id: `local-user-${crypto.randomUUID()}`,
      role: "user",
      content: question,
      sourceChunks: [],
      deliveryStatus: "sending",
      conversationKey,
    };
    setTransientUserMessage(optimisticUserMessage);

    try {
      await sendMutation.mutateAsync({
        question,
        sessionId,
        optimisticUserMessageId: optimisticUserMessage.id,
        context,
        contextKey,
        conversationRevision,
        mode,
        catalogScope: sessionQuery.data?.catalogScope ?? catalogScope,
      });
      setTransientUserMessage((currentMessage) =>
        currentMessage?.id === optimisticUserMessage.id ? null : currentMessage
      );
      return isCurrentRequest(conversationRevision) ? true : null;
    } catch (error) {
      if (isCurrentRequest(conversationRevision)) {
        if (
          error instanceof ApiError &&
          error.status === 422 &&
          error.validationErrors.some((item) => item.loc?.[0] === "body" && item.loc[1] === "mode")
        ) {
          setPreference({ conversationKey, mode: "hybrid" });
          setRejectedModeConversation(conversationKey);
        }
        setTransientUserMessage((currentMessage) =>
          currentMessage?.id === optimisticUserMessage.id
            ? { ...currentMessage, deliveryStatus: "failed" }
            : currentMessage
        );
      }
      return isCurrentRequest(conversationRevision) ? false : null;
    } finally {
      isSendInFlightRef.current = false;
    }
  };

  const visibleTransientMessage =
    transientUserMessage?.conversationKey === conversationKey ? transientUserMessage : null;

  return {
    catalogScope: sessionQuery.data?.catalogScope ?? catalogScope,
    mode,
    setMode: (selectedMode) => {
      setPreference({ conversationKey, mode: selectedMode });
      setRejectedModeConversation(null);
    },
    modeWarning:
      rejectedModeConversation === conversationKey
        ? "Modo de busca inválido. Usando híbrido como padrão. Confira a pergunta e envie novamente."
        : hasInvalidMode
          ? "O servidor informou um modo de busca inválido. O padrão para novas consultas é híbrido; você pode escolher outro modo."
          : null,
    messages: [
      ...(sessionQuery.data?.messages ?? []),
      ...(visibleTransientMessage ? [visibleTransientMessage] : []),
    ],
    loadedBulaId: sessionQuery.data?.bulaId ?? null,
    hasContextMismatch: sessionQuery.error instanceof ChatContextMismatchError,
    isLoading: sessionQuery.isLoading,
    isSending: sendMutation.isPending,
    loadError: sessionQuery.error,
    sendError:
      visibleTransientMessage?.id === sendMutation.variables?.optimisticUserMessageId
        ? sendMutation.error
        : null,
    sendQuestion,
    invalidatePendingConversation: () => {
      setPreference(null);
      setRejectedModeConversation(null);
      conversationRevisionRef.current += 1;
      setTransientUserMessage(null);
    },
  };
}
