from __future__ import annotations

import html as html_lib
import re
from dataclasses import asdict, dataclass
from typing import Iterable

from bs4 import BeautifulSoup

from .filings import EarningsFiling


@dataclass(frozen=True)
class Metric:
    company: str
    metric: str
    value: float | None
    unit: str | None
    fiscal_period: str | None
    source_url: str
    filing_accession: str
    evidence: str
    confidence: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Signal:
    company: str
    category: str
    direction: str
    evidence: str
    source_url: str
    filing_accession: str

    def to_dict(self) -> dict:
        return asdict(self)


MONEY_MULTIPLIERS = {
    "thousand": 1e3,
    "million": 1e6,
    "billion": 1e9,
}


def html_to_text(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", html_lib.unescape(text))


def _normalize_money(value: str, scale: str) -> float:
    return round(float(value.replace(",", "")) * MONEY_MULTIPLIERS[scale.lower()], 2)


def _find_money(text: str, patterns: Iterable[str]) -> tuple[float, str] | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return _normalize_money(match.group("value"), match.group("scale")), match.group(0)
    return None


def _find_percent(text: str, patterns: Iterable[str]) -> tuple[float, str] | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return float(match.group("value")), match.group(0)
    return None


def _metric(
    filing: EarningsFiling,
    name: str,
    found: tuple[float, str] | None,
    unit: str,
    confidence: str = "medium",
) -> Metric:
    if found is None:
        return Metric(
            filing.company_key,
            name,
            None,
            unit,
            filing.report_date,
            filing.source_url,
            filing.accession,
            "",
            "unavailable",
        )
    value, evidence = found
    return Metric(
        filing.company_key,
        name,
        value,
        unit,
        filing.report_date,
        filing.source_url,
        filing.accession,
        evidence[:500],
        confidence,
    )


def _money_pattern(prefix: str, max_chars: int = 140) -> str:
    return (
        rf"{prefix}.{{0,{max_chars}}}?\$\s*(?P<value>[0-9][0-9,.]*)\s*"
        rf"(?P<scale>billion|million|thousand)"
    )


def _percent_pattern(prefix: str, max_chars: int = 120) -> str:
    return rf"{prefix}.{{0,{max_chars}}}?(?P<value>[0-9]+(?:\.[0-9]+)?)\s*%"


def _sentence_signals(
    filing: EarningsFiling,
    text: str,
    category: str,
    positive_keywords: tuple[str, ...],
    negative_keywords: tuple[str, ...] = (),
) -> list[Signal]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    results: list[Signal] = []
    for sentence in sentences:
        lower = sentence.lower()
        direction: str | None = None
        if any(keyword in lower for keyword in positive_keywords):
            direction = "higher_commoditization"
        if any(keyword in lower for keyword in negative_keywords):
            direction = "lower_commoditization"
        if direction:
            results.append(
                Signal(
                    filing.company_key,
                    category,
                    direction,
                    sentence[:600],
                    filing.source_url,
                    filing.accession,
                )
            )
        if len(results) >= 4:
            break
    return results


def extract_company_data(filing: EarningsFiling, raw_html: str) -> tuple[list[Metric], list[Signal]]:
    text = html_to_text(raw_html)
    metrics: list[Metric] = []
    signals: list[Signal] = []

    if filing.company_key == "dell":
        metrics.extend(
            [
                _metric(
                    filing,
                    "ai_server_orders",
                    _find_money(text, [_money_pattern(r"AI(?:-optimized)?\s+server\s+orders")]),
                    "USD",
                ),
                _metric(
                    filing,
                    "ai_server_backlog",
                    _find_money(text, [_money_pattern(r"AI(?:-optimized)?\s+server\s+backlog")]),
                    "USD",
                ),
                _metric(
                    filing,
                    "ai_server_revenue",
                    _find_money(
                        text,
                        [
                            _money_pattern(r"AI(?:-optimized)?\s+server\s+revenue"),
                            _money_pattern(r"AI(?:-optimized)?\s+server\s+shipments"),
                        ],
                    ),
                    "USD",
                ),
                _metric(
                    filing,
                    "isg_revenue",
                    _find_money(text, [_money_pattern(r"Infrastructure\s+Solutions\s+Group.{0,80}?revenue", 180)]),
                    "USD",
                ),
                _metric(
                    filing,
                    "isg_operating_income",
                    _find_money(text, [_money_pattern(r"Infrastructure\s+Solutions\s+Group.{0,100}?operating\s+income", 200)]),
                    "USD",
                ),
                _metric(
                    filing,
                    "isg_operating_margin",
                    _find_percent(text, [_percent_pattern(r"Infrastructure\s+Solutions\s+Group.{0,120}?operating\s+margin", 220)]),
                    "percent",
                ),
            ]
        )
        signals += _sentence_signals(
            filing,
            text,
            "attach",
            (),
            ("storage attach", "attach rate", "pull-through", "dell ip storage", "networking attach"),
        )
        signals += _sentence_signals(
            filing,
            text,
            "pricing",
            ("competitive pricing", "pricing pressure", "price competition"),
        )
        signals += _sentence_signals(
            filing,
            text,
            "repeat_customers",
            ("customer concentration",),
            ("repeat customers", "repeat buyers", "customers returning"),
        )
    elif filing.company_key == "nvidia":
        metrics.extend(
            [
                _metric(
                    filing,
                    "data_center_revenue",
                    _find_money(text, [_money_pattern(r"Data\s+Center\s+revenue")]),
                    "USD",
                ),
                _metric(
                    filing,
                    "gross_margin",
                    _find_percent(
                        text,
                        [
                            _percent_pattern(r"GAAP\s+gross\s+margin"),
                            _percent_pattern(r"gross\s+margin\s+(?:was|of)"),
                        ],
                    ),
                    "percent",
                    "high",
                ),
                _metric(
                    filing,
                    "networking_revenue",
                    _find_money(text, [_money_pattern(r"networking\s+revenue")]),
                    "USD",
                ),
            ]
        )
        signals += _sentence_signals(
            filing,
            text,
            "supply",
            ("supply constraints eased", "supply improved", "lead times improved"),
            ("supply constrained", "supply constraints", "demand exceeds supply"),
        )
    elif filing.company_key == "smci":
        metrics.extend(
            [
                _metric(filing, "revenue", _find_money(text, [_money_pattern(r"net\s+sales"), _money_pattern(r"revenue")]), "USD"),
                _metric(
                    filing,
                    "gross_margin",
                    _find_percent(text, [_percent_pattern(r"gross\s+margin(?:\s+was|\s+of|\s+at)?")]),
                    "percent",
                    "high",
                ),
                _metric(
                    filing,
                    "operating_margin",
                    _find_percent(text, [_percent_pattern(r"operating\s+margin(?:\s+was|\s+of|\s+at)?")]),
                    "percent",
                ),
            ]
        )
        signals += _sentence_signals(
            filing,
            text,
            "pricing",
            ("competitive pricing", "pricing pressure", "price competition", "competitive environment"),
        )
    elif filing.company_key == "hpe":
        metrics.extend(
            [
                _metric(
                    filing,
                    "cloud_ai_revenue",
                    _find_money(text, [_money_pattern(r"Cloud\s*&\s*AI.{0,100}?revenue", 190), _money_pattern(r"Server.{0,100}?revenue", 190)]),
                    "USD",
                ),
                _metric(
                    filing,
                    "cloud_ai_operating_margin",
                    _find_percent(text, [_percent_pattern(r"Cloud\s*&\s*AI.{0,120}?operating\s+(?:profit\s+)?margin", 220)]),
                    "percent",
                ),
            ]
        )
        signals += _sentence_signals(
            filing,
            text,
            "attach",
            (),
            ("storage attach", "networking attach", "pull-through", "cross-sell"),
        )
        signals += _sentence_signals(
            filing,
            text,
            "pricing",
            ("competitive pricing", "pricing pressure", "price competition"),
        )

    signals += _sentence_signals(
        filing,
        text,
        "supply",
        ("lead times normalized", "lead times improved", "supply constraints eased", "supply normalized"),
        ("supply constrained", "supply constraints", "demand exceeds supply", "extended lead times"),
    )
    return metrics, signals
