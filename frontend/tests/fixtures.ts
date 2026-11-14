/** Explicit deterministic test fixtures; never imported by application code. */
import type { AgentResponse } from "@/lib/api-types";
export const testConversation = "39ae079b-9fa1-43e8-a165-2ad685b2b7d9";
export function agentFixture(
  overrides: Partial<AgentResponse> = {},
): AgentResponse {
  return {
    capability: "knowledge",
    status: "insufficient_evidence",
    answer:
      "The available source evidence is insufficient to answer this question reliably.",
    assessment: null,
    citations: [],
    error: null,
    model: "test-provider",
    retrieved_evidence_count: 1,
    selected_evidence_count: 1,
    abstention_reason: "model_abstained",
    conversation_id: testConversation,
    request_id: "001b05c2-721b-4f50-b132-ae454bd2e108",
    resolved_message: "Test question",
    context_used: false,
    ...overrides,
  };
}
export function historyFixture(
  response: AgentResponse,
  question = "Test question",
) {
  return {
    conversation_id: testConversation,
    messages: [
      {
        id: "user-message",
        request_id: response.request_id,
        role: "user",
        content: question,
        metadata: {},
        created_at: "2026-11-13T00:00:00Z",
        turn_number: 1,
      },
      {
        id: "assistant-message",
        request_id: response.request_id,
        role: "assistant",
        content: response.answer,
        metadata: response,
        created_at: "2026-11-13T00:00:01Z",
        turn_number: 1,
      },
    ],
    has_more: false,
    next_before_turn: null,
  };
}
