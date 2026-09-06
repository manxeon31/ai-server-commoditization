from ai_server_tracker.extract import Metric
from ai_server_tracker.filings import EarningsFiling
from ai_server_tracker.report import classify, render_report
from ai_server_tracker.scoring import calculate_score


def test_classification_boundaries():
    assert classify(25) == "Strongly differentiated"
    assert classify(40) == "Differentiated"
    assert classify(60) == "Moderate commoditization"
    assert classify(75) == "Materially commoditized"
    assert classify(90) == "Heavily commoditized"


def test_report_renders_core_sections():
    filing = EarningsFiling("dell", "DELL", "acc", "2026-09-01", None, "8-K", "x.htm", "2.02", "https://example.com")
    metric = Metric("dell", "isg_operating_margin", 15.0, "percent", None, "https://example.com", "acc", "evidence", "high")
    score = calculate_score([metric], [])
    report = render_report({"dell": filing}, [metric], [], score, None)
    assert "# AI Server Commoditization Monitor" in report
    assert "## Dell-specific indicators" in report
    assert "## Evidence" in report
