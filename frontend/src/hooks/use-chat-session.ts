import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import {
  askBulaQuestion,
  type AskResponse,
  type ChatSessionResponse,
  continueChatSession,
  getChatSession,
} from "@/api/chat";
import type { ChatTimeline, ChatTimelineMessage } from "@/components/chat/types";

interface SendQuestionVariables {
  question: string;
  sessionId: string | null;
  optimisticUserMessageId: string;
}

interface TransientChatMessage extends ChatTimelineMessage {
  conversationKey: string;
}

interface UseChatSessionOptions {
  bulaId: string;
  sessionId: string | null;
  onSessionCreated: (sessionId: string) => void;
}

interface UseChatSessionResult {
  messages: ChatTimelineMessage[];
  loadedBulaId: string | null;
  isLoading: boolean;
  isSending: boolean;
  loadError: Error | null;
  sendError: Error | null;
  sendQuestion: (question: string) => Promise<boolean>;
}

function buildSessionQueryKey(sessionId: string): readonly ["chat-session", string] {
  return ["chat-session", sessionId] as const;
}

function mapSessionToTimeline(session: ChatSessionResponse): ChatTimeline {
  return {
    sessionId: session.id,
    bulaId: session.bula_id,
    messages: session.messages.map((message) => ({
      id: message.id,
      role: message.role,
      content: message.content,
      sourceChunks: message.source_chunks ?? [],
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
    },
  ];
}

function buildConversationKey(bulaId: string, sessionId: string | null): string {
  return `${bulaId}:${sessionId ?? "new"}`;
}

export function useChatSession({
  bulaId,
  sessionId,
  onSessionCreated,
}: UseChatSessionOptions): UseChatSessionResult {
  const queryClient = useQueryClient();
  const isSendInFlightRef = useRef(false);
  const [transientUserMessage, setTransientUserMessage] = useState<TransientChatMessage | null>(
    null
  );
  const conversationKey = buildConversationKey(bulaId, sessionId);
  const sessionQuery = useQuery({
    queryKey: sessionId ? buildSessionQueryKey(sessionId) : ["chat-session", "new"],
    queryFn: async (): Promise<ChatTimeline> => {
      if (!sessionId) {
        throw new Error("A session identifier is required to load chat history.");
      }

      return mapSessionToTimeline(await getChatSession(sessionId));
    },
    enabled: Boolean(sessionId),
    staleTime: Number.POSITIVE_INFINITY,
  });

  const sendMutation = useMutation({
    mutationFn: async ({ question, sessionId: existingSessionId }: SendQuestionVariables) => {
      if (existingSessionId) {
        return continueChatSession(existingSessionId, { question, retrieval_mode: "dense" });
      }

      return askBulaQuestion(bulaId, { question, retrieval_mode: "dense" });
    },
    onSuccess: (response, variables) => {
      const nextSessionId = response.session_id;
      const nextQueryKey = buildSessionQueryKey(nextSessionId);
      const existingTimeline = variables.sessionId
        ? queryClient.getQueryData<ChatTimeline>(buildSessionQueryKey(variables.sessionId))
        : undefined;
      const newMessages = buildTurnMessages(
        variables.question,
        response,
        variables.optimisticUserMessageId
      );

      queryClient.setQueryData<ChatTimeline>(nextQueryKey, {
        sessionId: nextSessionId,
        bulaId,
        messages: [...(existingTimeline?.messages ?? []), ...newMessages],
      });
      void queryClient.invalidateQueries({ queryKey: ["chat-sessions"] });

      if (!variables.sessionId) {
        onSessionCreated(nextSessionId);
      }
    },
    retry: false,
  });

  const sendQuestion = async (question: string): Promise<boolean> => {
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
    isLoading: sessionQuery.isLoading,
    isSending: sendMutation.isPending,
    loadError: sessionQuery.error,
    sendError: sendMutation.error,
    sendQuestion,
  };
}
