import { describe, expect, it } from "vitest";
import { assessRisk, validateQuestion } from "@/lib/risk";
describe("backend-compatible risk matrix", () => {
  it.each([
    [1, 5, "Low"],
    [2, 3, "Medium"],
    [3, 5, "High"],
    [4, 4, "Critical"],
    [5, 5, "Critical"],
  ])("scores %i × %i as %s", (l, i, category) => {
    const result = assessRisk(l as number, i as number);
    expect(result.score).toBe((l as number) * (i as number));
    expect(result.category).toBe(category);
    expect(result.disclaimer).toContain("not a validated prediction");
  });
  it("covers all 25 cells with matching category boundaries", () => {
    for (let l = 1; l <= 5; l++)
      for (let i = 1; i <= 5; i++) {
        const r = assessRisk(l, i);
        const limits = {
          Low: [1, 5],
          Medium: [6, 10],
          High: [11, 15],
          Critical: [16, 25],
        };
        expect(r.score).toBeGreaterThanOrEqual(limits[r.category][0]);
        expect(r.score).toBeLessThanOrEqual(limits[r.category][1]);
      }
  });
  it.each([0, 6, -1, 2.5, NaN, Infinity, "4", true, null])(
    "rejects invalid ratings %s",
    (value) => {
      expect(() => assessRisk(value as number, 3)).toThrow(RangeError);
      expect(() => assessRisk(3, value as number)).toThrow(RangeError);
    },
  );
  it("validates trimmed questions and backend length bounds", () => {
    expect(validateQuestion("  ")).toBeTruthy();
    expect(validateQuestion("x".repeat(2001))).toBeTruthy();
    expect(validateQuestion("  What is NIST?  ")).toBeNull();
    expect(validateQuestion("x".repeat(2000))).toBeNull();
  });
});
