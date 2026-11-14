import { expect, it } from "vitest";
import { parseAgent, parseHistory, parseRisk } from "@/lib/contracts";
import { agentFixture, historyFixture } from "./fixtures";
it("accepts actual agent/history structure and preserves abstention without evidence", () => {
  expect(parseAgent(agentFixture()).citations).toEqual([]);
  expect(parseHistory(historyFixture(agentFixture())).messages).toHaveLength(2);
});
it.each([
  { status: "made_up" },
  { citations: [{}] },
  { status: "answered" },
  { assessment: { score: 25 } },
  { context_used: "yes" },
])("rejects malformed agent responses safely: %s", (override) => {
  expect(() => parseAgent({ ...agentFixture(), ...override })).toThrow(
    "unexpected response",
  );
});
it("rejects inconsistent risk products instead of replacing the server score", () => {
  const r = {
    likelihood: 4,
    impact: 5,
    score: 20,
    category: "Critical",
    interpretation: "Test",
    disclaimer: "Illustrative",
  };
  expect(parseRisk(r).score).toBe(20);
  expect(() => parseRisk({ ...r, score: 19 })).toThrow();
  expect(() => parseRisk({ ...r, category: "High" })).toThrow();
});
it("rejects incomplete assistant history metadata and impossible pagination", () => {
  const h = historyFixture(agentFixture());
  expect(() =>
    parseHistory({ ...h, has_more: true, next_before_turn: null }),
  ).toThrow();
  expect(() =>
    parseHistory({ ...h, messages: [{ ...h.messages[1], metadata: {} }] }),
  ).toThrow();
});
