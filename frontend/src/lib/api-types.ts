/** Mirrors backend/app/{agent,rag,retrieval}/schemas.py and memory/api.py. */
export type RiskCategory = "Low" | "Medium" | "High" | "Critical";
export interface RiskAssessment {
  likelihood: number;
  impact: number;
  score: number;
  category: RiskCategory;
  interpretation: string;
  disclaimer: string;
}
export interface Citation {
  document_id: string;
  document_title: string | null;
  filename: string;
  page_number: number;
  display_title: string;
  title_source: "metadata" | "filename";
  label: string;
}
export interface AnswerCitation extends Citation {
  evidence_id: string;
  chunk_id: string;
  chunk_index: number;
  quote: string;
  source_kind:
    "policy" | "framework" | "synthetic_incident" | "source_evidence";
}
export interface AgentRequest {
  message: string;
  likelihood?: number;
  impact?: number;
  top_k?: number;
  conversation_id?: string;
  request_id?: string;
}
export type AgentStatus =
  | "answered"
  | "assessed"
  | "insufficient_evidence"
  | "missing_input"
  | "needs_clarification"
  | "invalid_input"
  | "error";
export interface AgentResponse {
  capability: "knowledge" | "risk" | "none";
  status: AgentStatus;
  answer: string | null;
  assessment: RiskAssessment | null;
  citations: AnswerCitation[];
  error: {
    code: string;
    message: string;
    missing_inputs: ("likelihood" | "impact")[];
  } | null;
  model: string | null;
  retrieved_evidence_count: number;
  selected_evidence_count: number;
  abstention_reason: string | null;
  conversation_id: string | null;
  request_id: string | null;
  resolved_message: string | null;
  context_used: boolean;
}
export interface AskRequest {
  question: string;
  top_k?: number;
}
export interface AskResponse {
  question: string;
  answer: string;
  status: "answered" | "insufficient_evidence";
  citations: AnswerCitation[];
  retrieved_evidence_count: number;
  selected_evidence_count: number;
  model: string | null;
  grounding_mode: "verified_excerpts";
  abstention_reason: string | null;
}
export interface SearchRequest {
  query: string;
  top_k?: number;
  min_similarity?: number;
}
export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  document_title: string | null;
  filename: string;
  page_number: number;
  chunk_index: number;
  content: string;
  cosine_distance: number;
  similarity_score: number;
  citation: Citation;
}
export interface SearchResponse {
  query: string;
  results: RetrievedChunk[];
  result_count: number;
  min_similarity: number;
}
export interface HistoryMessage {
  id: string;
  request_id: string;
  role: string;
  content: string;
  metadata: Record<string, unknown>;
  created_at: string;
  turn_number: number;
}
export interface HistoryResponse {
  conversation_id: string;
  messages: HistoryMessage[];
  has_more: boolean;
  next_before_turn: number | null;
}
export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}
