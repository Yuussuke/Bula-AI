export function buildSourceChunkId(messageId: string, citationNumber: number): string {
  return `chat-message-${messageId}-source-${citationNumber}`;
}
