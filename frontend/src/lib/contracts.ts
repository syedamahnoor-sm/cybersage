/** Validate untrusted API JSON before rendering; never repair or invent evidence. */
import type {
  AgentResponse,
  AnswerCitation,
  HistoryResponse,
  HealthResponse,
  RiskAssessment,
} from "./api-types";
export class ContractError extends Error {
  constructor() {
    super(
      "CyberSage returned an unexpected response. Retry or check that the frontend and backend versions match.",
    );
  }
}
const record = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
const text = (v: unknown): v is string => typeof v === "string";
const nullableText = (v: unknown) => v === null || text(v);
const integer = (
  v: unknown,
  min = 0,
  max = Number.MAX_SAFE_INTEGER,
): v is number =>
  typeof v === "number" && Number.isInteger(v) && v >= min && v <= max;
const oneOf = (v: unknown, values: string[]) => text(v) && values.includes(v);
function requireValid(condition: boolean): asserts condition {
  if (!condition) throw new ContractError();
}
export function parseCitation(v: unknown): AnswerCitation {
  requireValid(
    record(v) &&
      [
        "document_id",
        "filename",
        "display_title",
        "label",
        "evidence_id",
        "chunk_id",
        "quote",
      ].every((k) => text(v[k]) && Boolean(v[k])) &&
      nullableText(v.document_title) &&
      oneOf(v.title_source, ["metadata", "filename"]) &&
      integer(v.page_number, 1) &&
      integer(v.chunk_index) &&
      oneOf(v.source_kind, [
        "policy",
        "framework",
        "synthetic_incident",
        "source_evidence",
      ]),
  );
  return v as unknown as AnswerCitation;
}
export function parseRisk(v: unknown): RiskAssessment {
  requireValid(
    record(v) &&
      integer(v.likelihood, 1, 5) &&
      integer(v.impact, 1, 5) &&
      integer(v.score, 1, 25) &&
      oneOf(v.category, ["Low", "Medium", "High", "Critical"]) &&
      text(v.interpretation) &&
      text(v.disclaimer),
  );
  const r = v as unknown as RiskAssessment;
  const expected =
    r.score <= 5
      ? "Low"
      : r.score <= 10
        ? "Medium"
        : r.score <= 15
          ? "High"
          : "Critical";
  requireValid(r.score === r.likelihood * r.impact && r.category === expected);
  return r;
}
export function parseAgent(v: unknown): AgentResponse {
  requireValid(
    record(v) &&
      oneOf(v.capability, ["knowledge", "risk", "none"]) &&
      oneOf(v.status, [
        "answered",
        "assessed",
        "insufficient_evidence",
        "missing_input",
        "needs_clarification",
        "invalid_input",
        "error",
      ]) &&
      nullableText(v.answer) &&
      Array.isArray(v.citations) &&
      nullableText(v.model) &&
      integer(v.retrieved_evidence_count) &&
      integer(v.selected_evidence_count) &&
      nullableText(v.abstention_reason) &&
      nullableText(v.conversation_id) &&
      nullableText(v.request_id) &&
      nullableText(v.resolved_message) &&
      typeof v.context_used === "boolean",
  );
  v.citations.forEach(parseCitation);
  if (v.assessment !== null) parseRisk(v.assessment);
  if (v.error !== null)
    requireValid(
      record(v.error) &&
        text(v.error.code) &&
        text(v.error.message) &&
        Array.isArray(v.error.missing_inputs) &&
        v.error.missing_inputs.every((k) => oneOf(k, ["likelihood", "impact"])),
    );
  requireValid(
    v.status !== "insufficient_evidence" || v.citations.length === 0,
  );
  requireValid(v.capability !== "risk" || v.citations.length === 0);
  requireValid(v.status !== "assessed" || v.assessment !== null);
  requireValid(
    v.status !== "answered" ||
      (v.capability === "knowledge" &&
        v.citations.length > 0 &&
        text(v.answer)),
  );
  return v as unknown as AgentResponse;
}
export function parseHistory(v: unknown): HistoryResponse {
  requireValid(
    record(v) &&
      text(v.conversation_id) &&
      Array.isArray(v.messages) &&
      typeof v.has_more === "boolean" &&
      (v.next_before_turn === null || integer(v.next_before_turn, 1)),
  );
  for (const row of v.messages) {
    requireValid(
      record(row) &&
        ["id", "request_id", "content", "created_at"].every((k) =>
          text(row[k]),
        ) &&
        oneOf(row.role, ["user", "assistant"]) &&
        record(row.metadata) &&
        integer(row.turn_number, 1),
    );
    if (row.role === "assistant") parseAgent(row.metadata);
  }
  requireValid(!v.has_more || v.next_before_turn !== null);
  return v as unknown as HistoryResponse;
}
export function parseHealth(v: unknown): HealthResponse {
  requireValid(
    record(v) && text(v.status) && text(v.service) && text(v.version),
  );
  return v as unknown as HealthResponse;
}
