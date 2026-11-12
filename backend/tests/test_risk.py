from itertools import product

from pydantic import ValidationError
import pytest

from app.agent.risk import assess_risk

CATEGORIES = [
    ["Low", "Low", "Low", "Low", "Low"],
    ["Low", "Low", "Medium", "Medium", "Medium"],
    ["Low", "Medium", "Medium", "High", "High"],
    ["Low", "Medium", "High", "Critical", "Critical"],
    ["Low", "Medium", "High", "Critical", "Critical"],
]


@pytest.mark.parametrize("likelihood,impact", list(product(range(1, 6), repeat=2)))
def test_all_25_matrix_cells(likelihood, impact):
    assessment = assess_risk(likelihood, impact)
    assert assessment.score == likelihood * impact
    assert assessment.category == CATEGORIES[likelihood - 1][impact - 1]
    assert assessment.likelihood == likelihood and assessment.impact == impact
    assert "not a validated prediction" in assessment.disclaimer


@pytest.mark.parametrize("field", ["likelihood", "impact"])
@pytest.mark.parametrize("value", [0, 6, -1, True, False, 1.0, 2.5, "4", None, [], float("nan")])
def test_strict_risk_inputs(field, value):
    inputs = {"likelihood": 4, "impact": 5, field: value}
    with pytest.raises(ValidationError):
        assess_risk(**inputs)
