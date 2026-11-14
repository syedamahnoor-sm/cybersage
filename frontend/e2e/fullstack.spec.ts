/** Deterministic browser tests. All API responses in this file are mocked. */
import { test, expect } from "@playwright/test";
import { agentFixture, testConversation } from "../tests/fixtures";
import type { AgentResponse } from "../src/lib/api-types";
import { assessRisk } from "../src/lib/risk";
test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/health", (route) =>
    route.fulfill({
      json: { status: "healthy", service: "CyberSage", version: "0.1.0" },
    }),
  );
});
test("mocked follow-up, abstention and refresh preserve a conversation without duplicate submissions", async ({
  page,
}) => {
  const questions: string[] = [];
  const responses: AgentResponse[] = [];
  const scopes: unknown[] = [];
  await page.route("**/api/v1/agent/invoke", async (route) => {
    const request = route.request().postDataJSON();
    questions.push(request.message);
    scopes.push(request.conversation_id);
    await new Promise((resolve) => setTimeout(resolve, 150));
    const response = agentFixture({
      request_id: request.request_id,
      answer:
        "The available source evidence is insufficient to answer this question reliably.",
      context_used: questions.length > 1,
      resolved_message:
        questions.length > 1
          ? "What does NIST CSF 2.0 say about recovery?"
          : request.message,
    });
    responses.push(response);
    await route.fulfill({ json: response });
  });
  await page.route(
    `**/api/v1/conversations/${testConversation}/messages?*`,
    (route) =>
      route.fulfill({
        json: {
          conversation_id: testConversation,
          has_more: false,
          next_before_turn: null,
          messages: questions.flatMap((q, index) => [
            {
              id: `u${index}`,
              request_id: responses[index].request_id,
              role: "user",
              content: q,
              metadata: {},
              created_at: "2026-11-13T00:00:00Z",
              turn_number: index + 1,
            },
            {
              id: `a${index}`,
              request_id: responses[index].request_id,
              role: "assistant",
              content: responses[index].answer,
              metadata: responses[index],
              created_at: "2026-11-13T00:00:01Z",
              turn_number: index + 1,
            },
          ]),
        },
      }),
  );
  await page.goto("/assistant");
  const input = page.getByRole("textbox", {
    name: "Your cybersecurity question",
  });
  await input.fill("What does NIST CSF 2.0 say about incident response?");
  await input.press("Enter");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/conversation=/);
  await expect(page.locator(".message-assistant")).toHaveCount(1);
  expect(questions).toHaveLength(1);
  await input.fill("What about recovery?");
  await input.press("Enter");
  await expect(
    page.getByText(/Contextual question: What does NIST/),
  ).toBeVisible();
  expect(scopes).toEqual([undefined, testConversation]);
  await expect(page.locator(".citation-card")).toHaveCount(0);
  await page.reload();
  await expect(page.locator(".message-assistant")).toHaveCount(2);
  await expect(
    page.getByText("What about recovery?", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "New conversation", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: /What would you like/ }),
  ).toBeVisible();
});
test("mocked risk confirmation is authoritative, invalid input is rejected and edited preview is distinct", async ({
  page,
}) => {
  const requests: Record<string, unknown>[] = [];
  await page.route("**/api/v1/agent/invoke", (route) => {
    const request = route.request().postDataJSON();
    requests.push(request);
    if (request.likelihood === 0)
      return route.fulfill({ status: 422, json: { detail: "Invalid rating" } });
    return route.fulfill({
      json: agentFixture({
        capability: "risk",
        status: "assessed",
        answer: null,
        model: null,
        request_id: request.request_id,
        assessment: assessRisk(request.likelihood, request.impact),
      }),
    });
  });
  await page.goto("/risk-analyzer");
  await page.getByRole("button", { name: "Likelihood 4: Likely" }).click();
  await page.getByRole("button", { name: "Impact 5: Severe" }).click();
  await expect(page.getByText("Server confirmed · Critical")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Confirm assessment", exact: true })
    .click();
  await expect(
    page.getByText("20/25 — Critical", { exact: true }),
  ).toBeVisible();
  expect(requests[0]).toMatchObject({
    message: "Calculate risk",
    likelihood: 4,
    impact: 5,
  });
  await page.getByRole("button", { name: "Impact 1: Negligible" }).click();
  await expect(page.getByText(/Inputs changed/)).toBeVisible();
  await expect(
    page.getByText("20/25 — Critical", { exact: true }),
  ).toBeVisible();
  const status = await page.evaluate(
    async () =>
      (
        await fetch("/api/v1/agent/invoke", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: "Calculate risk",
            likelihood: 0,
            impact: 5,
          }),
        })
      ).status,
  );
  expect(status).toBe(422);
});
test("mocked unavailable backend shows safe health and assistant errors", async ({
  page,
}) => {
  await page.route("**/api/v1/health", (route) =>
    route.fulfill({ status: 503, json: { detail: "private configuration" } }),
  );
  await page.route("**/api/v1/agent/invoke", (route) =>
    route.fulfill({ status: 503, json: { detail: "private configuration" } }),
  );
  await page.goto("/assistant");
  await expect(
    page.getByRole("button", { name: /API unavailable/ }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Your cybersecurity question" })
    .fill("What does NIST say?");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(
    page.getByRole("button", { name: "Retry request" }),
  ).toBeVisible();
  await expect(page.getByText("private configuration")).toHaveCount(0);
});
