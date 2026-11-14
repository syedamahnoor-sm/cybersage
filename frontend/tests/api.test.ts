import { expect, it, vi } from "vitest";
import { ApiError, createApiClient } from "@/lib/api";
import { agentFixture } from "./fixtures";
it("uses real endpoint paths, JSON request fields and no provider credentials", async () => {
  const transport = vi
    .fn<typeof fetch>()
    .mockImplementation(
      async (url) =>
        new Response(
          JSON.stringify(
            String(url).endsWith("/health")
              ? { status: "healthy", service: "CyberSage", version: "0.1.0" }
              : agentFixture(),
          ),
        ),
    );
  const client = createApiClient("http://localhost:8000/", transport);
  const payload = { message: "NIST response", request_id: "test-id", top_k: 5 };
  await client.invoke(payload);
  expect(transport).toHaveBeenCalledWith(
    "http://localhost:8000/api/v1/agent/invoke",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify(payload),
      credentials: "omit",
    }),
  );
  await client.health();
  await client.ask({ question: "Q" });
  await client.search({ query: "Q" });
  expect(transport.mock.calls.map((c) => c[0])).toEqual([
    "http://localhost:8000/api/v1/agent/invoke",
    "http://localhost:8000/api/v1/health",
    "http://localhost:8000/api/v1/rag/ask",
    "http://localhost:8000/api/v1/retrieval/search",
  ]);
});
it.each([404, 409, 422, 429, 500, 503, 504])(
  "handles HTTP %i without exposing server exception bodies",
  async (status) => {
    const client = createApiClient(
      "",
      vi
        .fn<typeof fetch>()
        .mockResolvedValue(
          new Response("private-provider-key/internal-host", { status }),
        ),
    );
    await expect(client.invoke({ message: "Q" })).rejects.toBeInstanceOf(
      ApiError,
    );
    await expect(client.health()).rejects.not.toThrow("private-provider-key");
  },
);
it("handles network and malformed JSON failures with a safe message", async () => {
  await expect(
    createApiClient(
      "",
      vi.fn<typeof fetch>().mockRejectedValue(new Error("secret")),
    ).health(),
  ).rejects.toThrow("Cannot reach CyberSage");
  await expect(
    createApiClient(
      "",
      vi.fn<typeof fetch>().mockResolvedValue(new Response("not-json")),
    ).health(),
  ).rejects.toThrow("Cannot reach CyberSage");
});
it("validates IDs and builds paged history URLs", async () => {
  const transport = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(
      JSON.stringify({
        conversation_id: "39ae079b-9fa1-43e8-a165-2ad685b2b7d9",
        messages: [],
        has_more: false,
        next_before_turn: null,
      }),
    ),
  );
  const client = createApiClient("", transport);
  expect(() => client.history("../../secret")).toThrow(
    "Invalid conversation ID",
  );
  await client.history("39ae079b-9fa1-43e8-a165-2ad685b2b7d9", 3);
  expect(transport.mock.calls[0][0]).toBe(
    "/api/v1/conversations/39ae079b-9fa1-43e8-a165-2ad685b2b7d9/messages?limit=10&before_turn=3",
  );
});
it("forwards cancellation without printing raw errors", async () => {
  const control = new AbortController();
  control.abort();
  const transport = vi
    .fn<typeof fetch>()
    .mockImplementation(async (_url, init) => {
      expect(init?.signal?.aborted).toBe(true);
      throw new Error("secret");
    });
  await expect(
    createApiClient("", transport).health(control.signal),
  ).rejects.toThrow("interrupted");
});
