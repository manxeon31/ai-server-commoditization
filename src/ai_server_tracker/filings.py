from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from .companies import CompanyConfig
from .sec_client import SecClient


@dataclass(frozen=True)
class EarningsFiling:
    company_key: str
    ticker: str
    accession: str
    filing_date: str
    report_date: str | None
    form: str
    primary_document: str
    items: str
    source_url: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _recent_rows(submissions: dict) -> list[dict[str, str]]:
    recent = submissions.get("filings", {}).get("recent", {})
    if not recent:
        return []
    keys = (
        "accessionNumber",
        "filingDate",
        "reportDate",
        "form",
        "primaryDocument",
        "items",
    )
    lengths = [len(recent.get(key, [])) for key in keys]
    if not lengths or min(lengths) == 0:
        return []
    rows: list[dict[str, str]] = []
    for index in range(min(lengths)):
        rows.append({key: recent[key][index] for key in keys})
    return rows


def _is_earnings_8k(row: dict[str, str]) -> bool:
    return row.get("form") == "8-K" and "2.02" in (row.get("items") or "")


def find_latest_earnings_filing(company: CompanyConfig, submissions: dict) -> EarningsFiling:
    rows = _recent_rows(submissions)
    candidates = [row for row in rows if _is_earnings_8k(row)]
    if not candidates:
        candidates = [row for row in rows if row.get("form") in {"10-Q", "10-K"}]
    if not candidates:
        raise ValueError(f"No earnings filing found for {company.ticker}")

    row = max(candidates, key=lambda item: item.get("filingDate") or "")
    accession = row["accessionNumber"]
    primary_document = row["primaryDocument"]
    return EarningsFiling(
        company_key=company.key,
        ticker=company.ticker,
        accession=accession,
        filing_date=row["filingDate"],
        report_date=row.get("reportDate") or None,
        form=row["form"],
        primary_document=primary_document,
        items=row.get("items") or "",
        source_url=SecClient.primary_document_url(company.cik, accession, primary_document),
    )


@dataclass(frozen=True)
class CycleDecision:
    status: str
    complete: bool
    state_changed: bool
    updated_state: dict


def evaluate_cycle(latest: dict[str, EarningsFiling], state: dict) -> CycleDecision:
    current_accessions = {key: filing.accession for key, filing in latest.items()}
    baseline = state.get("last_complete_filings") or {}

    if not baseline:
        updated = {
            "version": 1,
            "last_complete_filings": current_accessions,
            "baseline_established_on": date.today().isoformat(),
        }
        return CycleDecision("baseline", False, True, updated)

    changed = {
        key: accession != baseline.get(key)
        for key, accession in current_accessions.items()
    }
    complete = bool(changed) and all(changed.values())
    if complete:
        updated = dict(state)
        updated["last_complete_filings"] = current_accessions
        return CycleDecision("complete", True, True, updated)

    return CycleDecision("partial", False, False, state)
