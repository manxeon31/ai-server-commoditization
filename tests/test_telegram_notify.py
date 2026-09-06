from ai_server_tracker.telegram_notify import build_message


def _entry(score: float, confidence: str = "medium") -> dict:
    return {
        "score": {
            "overall_score": score,
            "confidence": confidence,
            "components": [
                {"category": "nvidia_value_capture_gap", "score": 88.0},
                {"category": "oem_margin_pressure", "score": 70.0},
                {"category": "pricing_intensity", "score": 65.0},
            ],
        }
    }


def test_build_message_includes_score_delta_and_report():
    message = build_message([_entry(47.0), _entry(53.5)], "https://example.com/report")
    assert "[AI Server Commoditization]" in message
    assert "53.5/100" in message
    assert "↑ 6.5 vs prior" in message
    assert "Nvidia Value Capture Gap: 88.0/100" in message
    assert "https://example.com/report" in message


def test_build_message_handles_first_scored_cycle():
    message = build_message([_entry(41.0, "low")], "https://example.com/report")
    assert "first scored cycle" in message
    assert "Confidence: low" in message
