/** Read-only real-service review; needs the completed fullstack run, makes no Groq calls. */
import { test, expect } from "@playwright/test";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
test("real-service desktop/mobile review has no console errors", async ({
  page,
}) => {
  const path = ".cache/milestone11/live-private.json";
  test.skip(!existsSync(path), "Complete the fullstack live run first");
  const report = JSON.parse(readFileSync(path, "utf8"));
  const cid = report.scenarios.find((s: { id: string }) => s.id === "A")
    .response.conversation_id;
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push("console_error");
  });
  page.on("pageerror", (error) => errors.push(error.name));
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1100 });
    for (const route of [
      "/",
      "/assistant",
      "/risk-analyzer",
      "/knowledge-base",
      "/about",
      `/assistant?conversation=${encodeURIComponent(cid)}`,
    ]) {
      await page.goto(route);
      await expect(
        page.getByRole("button", { name: /API reachable/ }),
      ).toBeVisible({ timeout: 15000 });
      await expect(page.locator("#main-content > div")).toHaveCSS(
        "opacity",
        "1",
      );
      if (route.includes("conversation="))
        await expect(page.locator(".message-assistant")).toHaveCount(2);
      expect
        .soft(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        )
        .toBe(true);
    }
  }
  report.read_only_ui_review = {
    widths: [1440, 390],
    routes_checked: 6,
    console_and_page_errors: errors,
    additional_groq_calls: 0,
    completed_at: new Date().toISOString(),
  };
  writeFileSync(path, JSON.stringify(report, null, 2));
  expect(errors).toEqual([]);
});
