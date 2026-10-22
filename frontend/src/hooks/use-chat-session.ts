import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import {
  askBulaQuestion,
  askCrossBulaQuestion,
  type AskResponse,
  type ChatContext,
  type ChatSessionResponse,
  continueChatSession,
  getChatSession,
} from "@/api/chat";
import type { ChatTimeline, ChatTimelineMessage } from "@/components/chat/types";

interface SendQuestionVariables {
  question: string;
  sessionId: string | null;
  optimisticUserMessageId: string;
  context: ChatContext;
  contextKey: string;
}

interface TransientChatMessage extends ChatTimelineMessage {
  conversationKey: string;
}

interface UseChatSessionOptions {
  context: ChatContext;
  sessionId: string | null;
  onSessionCreated: (sessionId: string) => void;
}

interface UseChatSessionResult {
  messages: ChatTimelineMessage[];
  loadedBulaId: string | null;
  hasContextMismatch: boolean;
  isLoading: boolean;
  isSending: boolean;
  loadError: Error | null;
  sendError: Error | null;
  sendQuestion: (question: string) => Promise<boolean>;
}

class ChatContextMismatchError extends Error {}

function buildSessionQueryKey(
  contextKey: string,
  sessionId: string
): readonly ["chat-session", string, string] {
  return ["chat-session", contextKey, sessionId] as const;
}

function mapSessionToTimeline(session: ChatSessionResponse): ChatTimeline {
  return {
    sessionId: session.id,
    bulaId: session.bula_id,
    scope: session.scope ?? "bula",
    messages: session.messages.map((message) => ({
      id: message.id,
      role: message.role,
      content: message.content,
      sourceChunks: message.source_chunks ?? [],
      retrievalMode: message.retrieval_mode,
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
      retrievalMode: response.retrieval_mode,
    },
  ];
}

function buildConversationKey(contextKey: string, sessionId: string | null): string {
  return `${contextKey}:${sessionId ?? "new"}`;
}

export function useChatSession({
  context,
  sessionId,
  onSessionCreated,
}: UseChatSessionOptions): UseChatSessionResult {
  const queryClient = useQueryClient();
  const isSendInFlightRef = useRef(false);
  const [transientUserMessage, setTransientUserMessage] = useState<TransientChatMessage | null>(
    null
  );
  const bulaId = context.scope === "bula" ? context.bulaId : null;
  const contextKey = `${context.scope}:${bulaId ?? "general"}`;
  const conversationKey = buildConversationKey(contextKey, sessionId);
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
    }: SendQuestionVariables) => {
      if (existingSessionId) {
        return continueChatSession(existingSessionId, { question });
      }

      if (questionContext.scope === "cross_bula") return askCrossBulaQuestion({ question });
      return askBulaQuestion(questionContext.bulaId, { question });
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
        sessionId: nextSessionId,
        bulaId: variables.context.scope === "bula" ? variables.context.bulaId : null,
        scope: variables.context.scope,
        messages: [...(existingTimeline?.messages ?? []), ...newMessages],
      });
      void queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });

      if (!variables.sessionId && variables.contextKey === contextKey) {
        onSessionCreated(nextSessionId);
      }
    },
    retry: false,
  });

  const sendQuestion = async (question: string): Promise<boolean> => {
    if (sessionId && (!sessionQuery.data || sessionQuery.error)) return false;
    if (isSendInFlightRef.current) {
      return false;
    }

    isSendInFlightRef.current = true;
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
      });
      setTransientUserMessage((currentMessage) =>
        currentMessage?.id === optimisticUserMessage.id ? null : currentMessage
      );
      return true;
    } catch {
      setTransientUserMessage((currentMessage) =>
        currentMessage?.id === optimisticUserMessage.id
          ? { ...currentMessage, deliveryStatus: "failed" }
          : currentMessage
      );
      return false;
    } finally {
      isSendInFlightRef.current = false;
    }
  };

  const visibleTransientMessage =
    transientUserMessage?.conversationKey === conversationKey ? transientUserMessage : null;

  return {
    messages: [
      ...(sessionQuery.data?.messages ?? []),
      ...(visibleTransientMessage ? [visibleTransientMessage] : []),
    ],
    loadedBulaId: sessionQuery.data?.bulaId ?? null,
    hasContextMismatch: sessionQuery.error instanceof ChatContextMismatchError,
    isLoading: sessionQuery.isLoading,
    isSending: sendMutation.isPending,
    loadError: sessionQuery.error,
    sendError: sendMutation.error,
    sendQuestion,
  };
}
