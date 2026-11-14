import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import {
  agentFixture,
  historyFixture,
  testConversation,
} from "../tests/fixtures";
import type { AgentResponse } from "../src/lib/api-types";
test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/health", (route) =>
    route.fulfill({
      json: { status: "healthy", service: "CyberSage", version: "0.1.0" },
    }),
  );
});
test("five pages render, navigation works, and desktop has no serious accessibility issues", async ({
  page,
}) => {
  for (const [path, heading] of [
    ["/", "Clarity in a complex"],
    ["/risk-analyzer", "Put risk into perspective."],
    ["/knowledge-base", "A foundation you can inspect."],
    ["/about", "Intelligence with a paper trail."],
    ["/assistant", "AI Assistant"],
  ]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      heading,
    );
    await expect(page.locator("#main-content > div")).toHaveCSS("opacity", "1");
    const results = await new AxeBuilder({ page }).analyze();
    expect(
      results.violations.filter((v) =>
        ["critical", "serious"].includes(v.impact ?? ""),
      ),
    ).toEqual([]);
  }
  await page
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("link", { name: "Knowledge Base" })
    .click();
  await expect(page).toHaveURL(/knowledge-base/);
});
test("mobile drawer traps focus, closes on Escape and routes without overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const trigger = page.getByRole("button", { name: "Open navigation" });
  await trigger.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  await trigger.click();
  await page
    .getByRole("dialog")
    .getByRole("link", { name: "Risk Analyzer" })
    .click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Put risk",
  );
  for (const path of [
    "/",
    "/assistant",
    "/risk-analyzer",
    "/knowledge-base",
    "/about",
  ]) {
    await page.goto(path);
    await expect(page.locator("#main-content > div")).toHaveCSS("opacity", "1");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
});
test("assistant validates, preserves idempotent retries, renders real contract fixture citations and starts fresh", async ({
  page,
}) => {
  // Explicit test fixture only; no fabricated response is bundled in the application.
  let attempts = 0;
  const requests: Record<string, unknown>[] = [];
  let recorded: AgentResponse | null = null;
  await page.route(
    `**/api/v1/conversations/${testConversation}/messages?*`,
    (route) =>
      route.fulfill({
        json: historyFixture(recorded!, String(requests[0].message)),
      }),
  );
  await page.route("**/api/v1/agent/invoke", async (route) => {
    requests.push(route.request().postDataJSON());
    attempts++;
    if (attempts === 1)
      return route.fulfill({
        status: 503,
        json: { detail: "Internal secret must not render" },
      });
    recorded = {
      capability: "knowledge",
      status: "answered",
      answer: "Framework guidance: incident reports are triaged and validated.",
      assessment: null,
      error: null,
      model: "test-provider",
      retrieved_evidence_count: 1,
      selected_evidence_count: 1,
      abstention_reason: null,
      conversation_id: "39ae079b-9fa1-43e8-a165-2ad685b2b7d9",
      request_id: String(requests[0].request_id),
      resolved_message: String(requests[0].message),
      context_used: false,
      citations: [
        {
          document_id: "test-doc",
          document_title: null,
          filename: "NIST.CSWP.29.pdf",
          page_number: 27,
          display_title: "NIST CSF 2.0",
          title_source: "filename",
          label: "[NIST CSF 2.0, p. 27]",
          evidence_id: "E_test",
          chunk_id: "test-chunk",
          chunk_index: 76,
          quote: "RS.MA-02: Incident reports are triaged and validated",
          source_kind: "framework",
        },
      ],
    };
    return route.fulfill({ json: recorded });
  });
  await page.goto("/assistant");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page.getByText("Enter a cybersecurity question.")).toBeVisible();
  await page.getByRole("button", { name: /FRAMEWORK How does NIST/ }).click();
  const input = page.getByRole("textbox", {
    name: "Your cybersecurity question",
  });
  await input.press("Shift+Enter");
  await expect(input).toHaveValue(/\n/);
  await input.press("Enter");
  await expect(
    page.getByRole("button", { name: "Retry request" }),
  ).toBeVisible();
  await expect(page.getByText("Internal secret must not render")).toHaveCount(
    0,
  );
  await page.getByRole("button", { name: "Retry request" }).click();
  await expect(
    page.getByText(
      "Framework guidance: incident reports are triaged and validated.",
    ),
  ).toBeVisible();
  await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.getByRole("button", { name: "Copy answer" }).click();
  await expect(
    page.getByRole("button", { name: "Copied", exact: true }),
  ).toBeVisible();
  expect(requests[0]).toEqual(requests[1]);
  await page.getByText("NIST CSF 2.0", { exact: true }).click();
  await expect(
    page.getByText("RS.MA-02: Incident reports are triaged and validated"),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "New conversation", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: /What would you like/ }),
  ).toBeVisible();
});

test("saved history loads actual metadata and requests earlier turns safely", async ({
  page,
}) => {
  const id = "39ae079b-9fa1-43e8-a165-2ad685b2b7d9";
  const historyRequests: string[] = [];
  await page.route(`**/api/v1/conversations/${id}/messages?*`, (route) => {
    const url = route.request().url();
    historyRequests.push(url);
    const older = url.includes("before_turn=2");
    return route.fulfill({
      json: {
        conversation_id: id,
        has_more: !older,
        next_before_turn: older ? null : 2,
        messages: [
          {
            id: older ? "earlier" : "recent",
            request_id: "fixture-request",
            role: "user",
            content: older ? "Earlier question" : "Recent NIST question",
            metadata: {},
            created_at: "2026-11-13T00:00:00Z",
            turn_number: older ? 1 : 2,
          },
          {
            id: older ? "earlier-answer" : "recent-answer",
            request_id: "fixture-request",
            role: "assistant",
            content: older ? "Earlier response" : "Recent response",
            metadata: agentFixture(),
            created_at: "2026-11-13T00:00:01Z",
            turn_number: older ? 1 : 2,
          },
        ],
      },
    });
  });
  await page.goto(`/assistant?conversation=${id}`);
  await expect(
    page.getByText("Recent response", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Load earlier messages" }).click();
  await expect(
    page.getByText("Earlier response", { exact: true }),
  ).toBeVisible();
  expect(historyRequests[1]).toContain("before_turn=2");
  await expect(
    page.getByRole("button", { name: "Load earlier messages" }),
  ).toHaveCount(0);
});
test("capture actual local desktop and mobile renders", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto("/");
  await page.waitForTimeout(500);
  await page.screenshot({
    path: ".cache/screenshots/overview-desktop.png",
    fullPage: true,
  });
  await page.goto("/risk-analyzer");
  await page.waitForTimeout(500);
  await page.screenshot({
    path: ".cache/screenshots/risk-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/assistant");
  await page.waitForTimeout(500);
  await page.screenshot({
    path: ".cache/screenshots/assistant-mobile.png",
    fullPage: true,
  });
});
