from __future__ import annotations

from datetime import date

from .extract import Metric, Signal
from .filings import EarningsFiling
from .scoring import ScoreResult


def classify(score: float | None) -> str:
    if score is None:
        return "Insufficient evidence"
    if score <= 25:
        return "Strongly differentiated"
    if score <= 40:
        return "Differentiated"
    if score <= 60:
        return "Moderate commoditization"
    if score <= 75:
        return "Materially commoditized"
    return "Heavily commoditized"


def _fmt_value(metric: Metric) -> str:
    if metric.value is None:
        return "Unavailable"
    if metric.unit == "USD":
        value = metric.value
        if value >= 1e9:
            return f"${value / 1e9:.2f}B"
        if value >= 1e6:
            return f"${value / 1e6:.1f}M"
        return f"${value:,.0f}"
    if metric.unit == "percent":
        return f"{metric.value:.1f}%"
    return f"{metric.value:g} {metric.unit or ''}".strip()


def render_report(
    filings: dict[str, EarningsFiling],
    metrics: list[Metric],
    signals: list[Signal],
    score: ScoreResult,
    previous_score: float | None,
) -> str:
    current = score.overall_score
    delta = None if current is None or previous_score is None else round(current - previous_score, 1)
    trend = "First scored cycle" if delta is None else "Increasing commoditization" if delta > 1 else "Decreasing commoditization" if delta < -1 else "Broadly stable"

    lines = [
        "# AI Server Commoditization Monitor",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## Executive signal",
        "",
        f"- Current index: **{current if current is not None else 'N/A'} / 100**",
        f"- Previous index: **{previous_score if previous_score is not None else 'N/A'}**",
        f"- Change: **{('+' if delta is not None and delta > 0 else '') + str(delta) if delta is not None else 'N/A'}**",
        f"- Trend: **{trend}**",
        f"- Classification: **{classify(current)}**",
        f"- Evidence confidence: **{score.confidence}**",
        f"- Scored weight coverage: **{score.available_weight:.0%}**",
        "",
        "> 0 = highly differentiated server layer; 100 = heavily commoditized. Missing components are excluded and remaining weights are re-normalized.",
        "",
        "## What changed this cycle",
        "",
    ]

    scored_components = sorted(
        [component for component in score.components if component.score is not None],
        key=lambda component: component.score or 0,
        reverse=True,
    )
    if scored_components:
        for component in scored_components[:5]:
            lines.append(f"- **{component.category.replace('_', ' ').title()} ({component.score:.1f})**: {component.explanation}")
    else:
        lines.append("- Insufficient extractable evidence to score this cycle.")

    lines += ["", "## Company dashboard", "", "| Company | Metric | Value | Confidence |", "|---|---|---:|---|"]
    for metric in metrics:
        lines.append(f"| {metric.company.upper()} | {metric.metric.replace('_', ' ')} | {_fmt_value(metric)} | {metric.confidence} |")

    lines += ["", "## Dell-specific indicators", ""]
    dell_metrics = [metric for metric in metrics if metric.company == "dell"]
    for metric in dell_metrics:
        lines.append(f"- **{metric.metric.replace('_', ' ').title()}**: {_fmt_value(metric)}")
    dell_signals = [signal for signal in signals if signal.company == "dell"]
    if dell_signals:
        lines.append("")
        lines.append("Qualitative evidence:")
        for signal in dell_signals[:8]:
            lines.append(f"- `{signal.category}`: {signal.evidence}")

    lines += ["", "## Where value is being captured", ""]
    nvidia_margin = next((m for m in metrics if m.company == "nvidia" and m.metric == "gross_margin" and m.value is not None), None)
    smci_margin = next((m for m in metrics if m.company == "smci" and m.metric == "gross_margin" and m.value is not None), None)
    if nvidia_margin and smci_margin:
        lines.append(f"NVIDIA gross margin is {_fmt_value(nvidia_margin)} versus Supermicro gross margin of {_fmt_value(smci_margin)}. Treat this as a directional value-capture comparison, not an accounting-equivalent margin comparison.")
    else:
        lines.append("The current filings did not expose enough comparable margin proxies for a concise value-capture comparison.")

    lines += ["", "## Commoditization components", "", "| Indicator | Score | Weight | Confidence |", "|---|---:|---:|---|"]
    for component in score.components:
        value = "N/A" if component.score is None else f"{component.score:.1f}"
        lines.append(f"| {component.category.replace('_', ' ')} | {value} | {component.weight:.0%} | {component.confidence} |")

    lines += [
        "",
        "## Three implications for Dell",
        "",
        "1. **Watch gross profit, not GPU-inflated revenue.** If AI revenue grows much faster than Dell's profit pool, value is migrating upstream.",
        "2. **Dell-IP attach is the strategic escape hatch.** Storage, networking, services, management, cooling and lifecycle pull-through matter more as GPU trays standardize.",
        "3. **Procurement behavior is an early warning.** More RFPs specified around NVIDIA architecture, price and delivery rather than Dell-specific architecture would be a strong commoditization signal.",
        "",
        "## Evidence",
        "",
    ]
    for filing in filings.values():
        lines.append(f"- {filing.ticker}: [{filing.form} filed {filing.filing_date}]({filing.source_url}) — accession `{filing.accession}`")

    lines += [
        "",
        "## Method notes",
        "",
        "This is an SEC-first deterministic monitor. Missing data stays missing. The architecture-convergence component is intentionally unscored in v1 because SEC filings are a poor source for product-topology comparisons. Add a separate official-product-source collector before scoring that dimension.",
        "",
    ]
    return "\n".join(lines)
