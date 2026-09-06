from ai_server_tracker.extract import Metric, Signal
from ai_server_tracker.scoring import calculate_score


def metric(company: str, name: str, value: float | None) -> Metric:
    return Metric(company, name, value, "percent", "2026Q2", "https://example.com", "acc", "evidence", "high" if value is not None else "unavailable")


def signal(company: str, category: str, direction: str) -> Signal:
    return Signal(company, category, direction, "evidence", "https://example.com", "acc")


def test_score_renormalizes_missing_components():
    metrics = [
        metric("nvidia", "gross_margin", 75.0),
        metric("smci", "gross_margin", 11.0),
        metric("dell", "isg_operating_margin", 15.0),
    ]
    result = calculate_score(metrics, [])
    assert result.overall_score is not None
    assert result.available_weight == 0.5
    architecture = next(c for c in result.components if c.category == "architecture_convergence")
    assert architecture.score is None


def test_pricing_pressure_increases_score_coverage():
    metrics = [metric("nvidia", "gross_margin", 75.0), metric("smci", "gross_margin", 11.0)]
    base = calculate_score(metrics, [])
    pressured = calculate_score(metrics, [signal("smci", "pricing", "higher_commoditization")])
    assert pressured.available_weight > base.available_weight


def test_no_evidence_returns_unavailable_score():
    result = calculate_score([], [])
    assert result.overall_score is None
    assert result.confidence == "unavailable"
