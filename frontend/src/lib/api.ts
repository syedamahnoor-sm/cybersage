import type {
  AgentRequest,
  AgentResponse,
  AskRequest,
  AskResponse,
  HealthResponse,
  HistoryResponse,
  SearchRequest,
  SearchResponse,
} from "./api-types";
import {
  ContractError,
  parseAgent,
  parseHealth,
  parseHistory,
} from "./contracts";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
const messages: Record<number, string> = {
  404: "This conversation could not be found. Start a new conversation.",
  409: "This conversation changed. Retry the same request or start a new conversation.",
  422: "Check your input. Questions must be 1–2,000 characters and numerical ratings must be integers from 1 to 5.",
  429: "The service is busy. Wait a moment before retrying.",
  503: "The intelligence service is unavailable. Check that FastAPI, PostgreSQL and the provider are configured.",
  504: "The request timed out. You can retry the same request safely.",
};

export function createApiClient(
  base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "",
  transport: typeof fetch = fetch,
) {
  const prefix = base.replace(/\/$/, "");
  async function request<T>(
    path: string,
    body?: unknown,
    signal?: AbortSignal,
    parse?: (value: unknown) => T,
  ): Promise<T> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120_000);
    const abort = () => controller.abort();
    signal?.addEventListener("abort", abort, { once: true });
    if (signal?.aborted) controller.abort();
    try {
      const response = await transport(`${prefix}/api/v1${path}`, {
        method: body === undefined ? "GET" : "POST",
        cache: "no-store",
        credentials: "omit",
        headers: { "Content-Type": "application/json" },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
        signal: controller.signal,
      });
      if (!response.ok)
        throw new ApiError(
          response.status,
          messages[response.status] ??
            "The request could not be completed. Please try again.",
        );
      const value: unknown = await response.json();
      return parse ? parse(value) : (value as T);
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (error instanceof ContractError) throw new ApiError(0, error.message);
      if (controller.signal.aborted)
        throw new ApiError(
          0,
          "The request was interrupted or timed out. Retry when ready.",
        );
      throw new ApiError(
        0,
        "Cannot reach CyberSage. Check the API connection and try again.",
      );
    } finally {
      clearTimeout(timeout);
      signal?.removeEventListener("abort", abort);
    }
  }
  return {
    health: (signal?: AbortSignal) =>
      request<HealthResponse>("/health", undefined, signal, parseHealth),
    invoke: (body: AgentRequest, signal?: AbortSignal) =>
      request<AgentResponse>("/agent/invoke", body, signal, parseAgent),
    ask: (body: AskRequest, signal?: AbortSignal) =>
      request<AskResponse>("/rag/ask", body, signal),
    search: (body: SearchRequest, signal?: AbortSignal) =>
      request<SearchResponse>("/retrieval/search", body, signal),
    history: (id: string, before?: number, signal?: AbortSignal) => {
      if (
        !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
          id,
        )
      )
        throw new ApiError(422, "Invalid conversation ID.");
      return request<HistoryResponse>(
        `/conversations/${encodeURIComponent(id)}/messages?limit=10${before ? `&before_turn=${before}` : ""}`,
        undefined,
        signal,
        parseHistory,
      );
    },
  };
}
export const api = createApiClient();
