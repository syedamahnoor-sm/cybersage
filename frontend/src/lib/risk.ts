import type { RiskAssessment, RiskCategory } from "./api-types";
export const ratings = [1, 2, 3, 4, 5] as const;
export function assessRisk(likelihood: number, impact: number): RiskAssessment {
  if (
    ![likelihood, impact].every((n) => Number.isInteger(n) && n >= 1 && n <= 5)
  )
    throw new RangeError("Use whole numbers from 1 to 5.");
  const score = likelihood * impact;
  const category: RiskCategory =
    score <= 5
      ? "Low"
      : score <= 10
        ? "Medium"
        : score <= 15
          ? "High"
          : "Critical";
  return {
    likelihood,
    impact,
    score,
    category,
    interpretation: `Likelihood ${likelihood}/5 and impact ${impact}/5 produce ${score}/25, classified as ${category} in this illustrative matrix.`,
    disclaimer:
      "Illustrative qualitative matrix; not a validated prediction of real-world cyber risk.",
  };
}
export function validateQuestion(message: string): string | null {
  if (!message.trim()) return "Enter a cybersecurity question.";
  if (message.trim().length > 2000)
    return "Keep your question within 2,000 characters.";
  return null;
}
