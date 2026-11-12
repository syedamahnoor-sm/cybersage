"""Pure, deterministic illustrative risk matrix. No model or I/O is used."""

from app.agent.schemas import RiskAssessment, RiskInputs


def assess_risk(likelihood: int, impact: int) -> RiskAssessment:
    inputs = RiskInputs(likelihood=likelihood, impact=impact)
    score = inputs.likelihood * inputs.impact
    if score <= 5:
        category = "Low"
    elif score <= 10:
        category = "Medium"
    elif score <= 15:
        category = "High"
    else:
        category = "Critical"
    return RiskAssessment(
        **inputs.model_dump(), score=score, category=category,
        interpretation=f"Likelihood {inputs.likelihood}/5 and impact {inputs.impact}/5 "
                       f"produce {score}/25, classified as {category} in this illustrative matrix.",
    )
