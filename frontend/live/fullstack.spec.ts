/** Opt-in real-services validation. No route interception or synthetic answer fixtures. */
import { test, expect } from "@playwright/test";
import { mkdirSync, writeFileSync, existsSync, renameSync } from "node:fs";
import { createHash } from "node:crypto";
import type { AgentResponse } from "../src/lib/api-types";

test("real FastAPI/Groq RAG, memory, risk, abstention and refresh", async ({
  page,
}) => {
  const root = ".cache/milestone11";
  mkdirSync(root, { recursive: true });
  if (existsSync(`${root}/live-private.json`))
    renameSync(
      `${root}/live-private.json`,
      `${root}/archive-${Date.now()}.json`,
    );
  const records: Record<string, unknown> = {
    started_at: new Date().toISOString(),
    mocked: false,
    scenarios: [],
    console_errors: [],
  };
  const scenarios = records.scenarios as Record<string, unknown>[];
  page.on("pageerror", (error) =>
    (records.console_errors as string[]).push(error.name),
  );
  const save = () =>
    writeFileSync(
      `${root}/live-private.json`,
      JSON.stringify(records, null, 2),
    );
  async function cooldown() {
    await page.waitForTimeout(35_000);
    await page.waitForTimeout(30_000);
  }
  async function ask(id: string, question: string) {
    await page
      .getByRole("textbox", { name: "Your cybersecurity question" })
      .fill(question);
    const started = Date.now();
    const responsePromise = page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/agent/invoke") &&
        r.request().method() === "POST",
      { timeout: 150_000 },
    );
    await page.getByRole("button", { name: "Send question" }).click();
    const response = await responsePromise;
    let body: AgentResponse;
    try {
      body = (await response.json()) as AgentResponse;
    } catch {
      scenarios.push({
        id,
        question,
        http_status: response.status(),
        error: "non_json_response",
        duration_seconds: (Date.now() - started) / 1000,
      });
      save();
      throw new Error(
        "The live API returned a non-JSON response; safe status recorded.",
      );
    }
    scenarios.push({
      id,
      question,
      http_status: response.status(),
      duration_seconds: (Date.now() - started) / 1000,
      response: body,
      request: response.request().postDataJSON(),
    });
    save();
    console.log(`${id}: HTTP ${response.status()} / ${body.status ?? "error"}`);
    await expect(
      page.getByRole("button", { name: "Send question" }),
    ).toBeEnabled({ timeout: 15000 });
    return body;
  }
  try {
    await page.setViewportSize({ width: 1440, height: 1100 });
    await page.goto("/");
    await expect(
      page.getByRole("button", { name: /API reachable/ }),
    ).toBeVisible({ timeout: 15000 });
    await expect(page.locator("#main-content > div")).toHaveCSS("opacity", "1");
    await page.screenshot({ path: `${root}/overview.png`, fullPage: true });
    await page.getByRole("link", { name: "Open AI Assistant" }).click();
    const a = await ask(
      "A",
      "What does NIST CSF 2.0 say about incident response?",
    );
    expect.soft(a.status).toBe("answered");
    expect.soft(a.citations?.length ?? 0).toBeGreaterThan(0);
    await expect(page).toHaveURL(/conversation=/, { timeout: 10000 });
    await page.screenshot({
      path: `${root}/assistant-citations.png`,
      fullPage: true,
    });
    await cooldown();
    const b = await ask("B", "What about recovery?");
    expect.soft(b.conversation_id).toBe(a.conversation_id);
    expect.soft(b.context_used).toBe(true);
    expect.soft(b.resolved_message).toMatch(/NIST.*recovery/i);
    expect.soft(b.retrieved_evidence_count).toBeGreaterThan(0);
    await page
      .getByText("What about recovery?", { exact: true })
      .scrollIntoViewIfNeeded();
    await page.screenshot({ path: `${root}/memory.png`, fullPage: true });
    await page.reload();
    await expect(
      page.getByText("What about recovery?", { exact: true }),
    ).toBeVisible({ timeout: 15000 });
    await expect(page.locator(".message-assistant")).toHaveCount(2);
    const history = await page.request.get(
      `/api/v1/conversations/${a.conversation_id}/messages?limit=10`,
    );
    const h = await history.json();
    records.persistence = {
      http_status: history.status(),
      message_count: h.messages?.length,
      original_questions: h.messages
        ?.filter((m: { role: string }) => m.role === "user")
        .map((m: { content: string }) => m.content),
      history: h,
    };
    expect.soft(h.messages?.length).toBe(4);
    save();
    await page
      .getByRole("navigation", { name: "Primary navigation" })
      .getByRole("link", { name: "Risk Analyzer" })
      .click();
    await page.getByRole("button", { name: "Likelihood 4: Likely" }).click();
    await page.getByRole("button", { name: "Impact 5: Severe" }).click();
    const rp = page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/agent/invoke") &&
        r.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Confirm assessment", exact: true })
      .click();
    const rr = await rp;
    const c = await rr.json();
    scenarios.push({ id: "C", http_status: rr.status(), response: c });
    save();
    await expect(
      page.getByText("Server confirmed · Critical", { exact: true }),
    ).toBeVisible();
    expect.soft(c.assessment?.score).toBe(20);
    expect.soft(c.citations).toEqual([]);
    await page.getByRole("heading", { level: 1 }).click();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({
      path: `${root}/risk-confirmed.png`,
      fullPage: true,
    });
    const invalid = await page.request.post("/api/v1/agent/invoke", {
      data: { message: "Calculate risk", likelihood: 0, impact: 5 },
    });
    records.invalid_input = { http_status: invalid.status() };
    expect.soft(invalid.status()).toBe(422);
    await cooldown();
    await page
      .getByRole("button", { name: "New conversation", exact: true })
      .click();
    const d = await ask(
      "D",
      "What is the cybersecurity policy of Mars in 2050?",
    );
    expect.soft(d.status).toBe("insufficient_evidence");
    expect.soft(d.citations).toEqual([]);
    expect.soft(d.conversation_id).not.toBe(a.conversation_id);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`/assistant?conversation=${a.conversation_id}`);
    await expect(page.locator(".message-assistant")).toHaveCount(2);
    expect
      .soft(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      )
      .toBe(true);
    await page.screenshot({
      path: `${root}/memory-mobile.png`,
      fullPage: true,
    });
    records.conversation_sha256 = createHash("sha256")
      .update(a.conversation_id!)
      .digest("hex");
    records.finished_at = new Date().toISOString();
    records.completed = true;
    expect.soft(records.console_errors).toEqual([]);
  } finally {
    save();
  }
});
