from ai_server_tracker.companies import COMPANY_BY_KEY
from ai_server_tracker.filings import EarningsFiling, evaluate_cycle, find_latest_earnings_filing


def submissions_fixture():
    return {
        "filings": {
            "recent": {
                "accessionNumber": ["0001-26-000003", "0001-26-000002", "0001-26-000001"],
                "filingDate": ["2026-08-30", "2026-08-29", "2026-05-20"],
                "reportDate": ["2026-07-31", "2026-07-31", "2026-04-30"],
                "form": ["8-K", "8-K", "10-Q"],
                "primaryDocument": ["other.htm", "earnings.htm", "q.htm"],
                "items": ["8.01", "2.02,9.01", ""],
            }
        }
    }


def make_filing(key: str, accession: str) -> EarningsFiling:
    return EarningsFiling(key, key.upper(), accession, "2026-08-01", None, "8-K", "x.htm", "2.02", "https://example.com")


def test_finds_latest_earnings_8k_not_latest_generic_8k():
    filing = find_latest_earnings_filing(COMPANY_BY_KEY["dell"], submissions_fixture())
    assert filing.accession == "0001-26-000002"
    assert filing.form == "8-K"


def test_first_run_establishes_baseline():
    latest = {key: make_filing(key, f"{key}-1") for key in ("dell", "nvidia", "hpe", "smci")}
    decision = evaluate_cycle(latest, {"version": 1, "last_complete_filings": {}})
    assert decision.status == "baseline"
    assert decision.state_changed is True
    assert decision.complete is False


def test_partial_cycle_does_not_advance_baseline():
    baseline = {key: f"{key}-1" for key in ("dell", "nvidia", "hpe", "smci")}
    latest = {key: make_filing(key, f"{key}-2" if key == "dell" else baseline[key]) for key in baseline}
    state = {"version": 1, "last_complete_filings": baseline}
    decision = evaluate_cycle(latest, state)
    assert decision.status == "partial"
    assert decision.state_changed is False
    assert decision.updated_state == state


def test_complete_cycle_requires_all_four_new_filings():
    baseline = {key: f"{key}-1" for key in ("dell", "nvidia", "hpe", "smci")}
    latest = {key: make_filing(key, f"{key}-2") for key in baseline}
    decision = evaluate_cycle(latest, {"version": 1, "last_complete_filings": baseline})
    assert decision.status == "complete"
    assert decision.complete is True
    assert decision.updated_state["last_complete_filings"]["smci"] == "smci-2"
