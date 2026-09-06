from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .companies import COMPANIES
from .extract import extract_company_data
from .filings import EarningsFiling, evaluate_cycle, find_latest_earnings_filing
from .report import render_report
from .scoring import calculate_score
from .sec_client import SecClient

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE = ROOT / "data" / "state.json"
DEFAULT_HISTORY = ROOT / "data" / "history.json"
DEFAULT_REPORTS = ROOT / "reports"


def _load_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_github_output(path: str | None, values: dict[str, str]) -> None:
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def run(
    state_path: Path = DEFAULT_STATE,
    history_path: Path = DEFAULT_HISTORY,
    reports_dir: Path = DEFAULT_REPORTS,
    github_output: str | None = None,
) -> int:
    user_agent = os.getenv("SEC_USER_AGENT", "").strip()
    if not user_agent:
        raise SystemExit("SEC_USER_AGENT is required. Set a repository Actions secret with a contact-aware SEC User-Agent.")

    client = SecClient(user_agent=user_agent)
    latest: dict[str, EarningsFiling] = {}
    for company in COMPANIES:
        submissions = client.get_submissions(company.cik)
        latest[company.key] = find_latest_earnings_filing(company, submissions)
        LOGGER.info("%s latest earnings filing: %s", company.ticker, latest[company.key].accession)

    state = _load_json(state_path, {"version": 1, "last_complete_filings": {}})
    decision = evaluate_cycle(latest, state)

    if decision.status == "baseline":
        _save_json(state_path, decision.updated_state)
        LOGGER.info("Baseline established. No report generated on first run.")
        _write_github_output(github_output, {"state_changed": "true", "report_created": "false", "cycle_status": "baseline"})
        return 0

    if decision.status == "partial":
        LOGGER.info("Partial earnings cycle. Waiting until all four companies have newer earnings filings.")
        _write_github_output(github_output, {"state_changed": "false", "report_created": "false", "cycle_status": "partial"})
        return 0

    metrics = []
    signals = []
    for company in COMPANIES:
        filing = latest[company.key]
        source_url, raw_html = client.get_earnings_document(company.cik, filing.accession, filing.primary_document)
        filing = EarningsFiling(**{**asdict(filing), "source_url": source_url})
        latest[company.key] = filing
        company_metrics, company_signals = extract_company_data(filing, raw_html)
        metrics.extend(company_metrics)
        signals.extend(company_signals)

    score = calculate_score(metrics, signals)
    history = _load_json(history_path, [])
    previous_score = history[-1].get("score", {}).get("overall_score") if history else None

    reports_dir.mkdir(parents=True, exist_ok=True)
    report_name = f"{date.today().isoformat()}-ai-server-commoditization.md"
    report_path = reports_dir / report_name
    report_path.write_text(render_report(latest, metrics, signals, score, previous_score), encoding="utf-8")

    history.append(
        {
            "generated_on": date.today().isoformat(),
            "filings": {key: filing.to_dict() for key, filing in latest.items()},
            "metrics": [metric.to_dict() for metric in metrics],
            "signals": [signal.to_dict() for signal in signals],
            "score": score.to_dict(),
            "report_path": str(report_path.relative_to(ROOT)),
        }
    )
    _save_json(history_path, history)
    _save_json(state_path, decision.updated_state)

    LOGGER.info("Generated %s with index %s", report_path, score.overall_score)
    _write_github_output(
        github_output,
        {
            "state_changed": "true",
            "report_created": "true",
            "cycle_status": "complete",
            "report_path": str(report_path.relative_to(ROOT)),
            "score": "N/A" if score.overall_score is None else str(score.overall_score),
        },
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Track AI-server commoditization after complete earnings cycles.")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS)
    parser.add_argument("--github-output", default=os.getenv("GITHUB_OUTPUT"))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    return run(args.state, args.history, args.reports_dir, args.github_output)


if __name__ == "__main__":
    raise SystemExit(main())
