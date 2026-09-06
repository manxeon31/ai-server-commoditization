from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean

from .extract import Metric, Signal


WEIGHTS = {
    "oem_margin_pressure": 0.30,
    "nvidia_value_capture_gap": 0.20,
    "dell_attach": 0.15,
    "pricing_intensity": 0.15,
    "architecture_convergence": 0.10,
    "supply_normalization": 0.10,
}


@dataclass(frozen=True)
class ComponentScore:
    category: str
    score: float | None
    weight: float
    confidence: str
    explanation: str
    evidence: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ScoreResult:
    overall_score: float | None
    confidence: str
    components: list[ComponentScore]
    available_weight: float

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "confidence": self.confidence,
            "available_weight": self.available_weight,
            "components": [component.to_dict() for component in self.components],
        }


def _metric_value(metrics: list[Metric], company: str, name: str) -> float | None:
    for metric in metrics:
        if metric.company == company and metric.metric == name:
            return metric.value
    return None


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _oem_margin_score(metrics: list[Metric]) -> ComponentScore:
    evidence: list[str] = []
    scores: list[float] = []

    smci_gm = _metric_value(metrics, "smci", "gross_margin")
    if smci_gm is not None:
        score = _clamp(95 - 4.0 * smci_gm)
        scores.append(score)
        evidence.append(f"SMCI gross margin {smci_gm:.1f}%")

    dell_isg = _metric_value(metrics, "dell", "isg_operating_margin")
    if dell_isg is not None:
        score = _clamp(90 - 3.0 * dell_isg)
        scores.append(score)
        evidence.append(f"Dell ISG operating margin {dell_isg:.1f}%")

    hpe_margin = _metric_value(metrics, "hpe", "cloud_ai_operating_margin")
    if hpe_margin is not None:
        score = _clamp(90 - 3.0 * hpe_margin)
        scores.append(score)
        evidence.append(f"HPE Cloud & AI operating margin {hpe_margin:.1f}%")

    if not scores:
        return ComponentScore("oem_margin_pressure", None, WEIGHTS["oem_margin_pressure"], "unavailable", "No usable OEM margin metrics.", [])
    return ComponentScore(
        "oem_margin_pressure",
        round(mean(scores), 1),
        WEIGHTS["oem_margin_pressure"],
        "medium",
        "Lower OEM margins imply more commodity-like economics.",
        evidence,
    )


def _value_capture_score(metrics: list[Metric]) -> ComponentScore:
    nvidia_gm = _metric_value(metrics, "nvidia", "gross_margin")
    oem_values = [
        value
        for value in (
            _metric_value(metrics, "smci", "gross_margin"),
            _metric_value(metrics, "dell", "isg_operating_margin"),
            _metric_value(metrics, "hpe", "cloud_ai_operating_margin"),
        )
        if value is not None
    ]
    if nvidia_gm is None or not oem_values:
        return ComponentScore("nvidia_value_capture_gap", None, WEIGHTS["nvidia_value_capture_gap"], "unavailable", "Need NVIDIA gross margin and at least one OEM margin proxy.", [])
    oem_avg = mean(oem_values)
    gap = nvidia_gm - oem_avg
    score = _clamp((gap - 20.0) * 2.0)
    return ComponentScore(
        "nvidia_value_capture_gap",
        round(score, 1),
        WEIGHTS["nvidia_value_capture_gap"],
        "medium",
        "A wider NVIDIA-to-OEM margin gap suggests economic value is concentrated upstream in accelerator IP.",
        [f"NVIDIA gross margin {nvidia_gm:.1f}%", f"OEM margin proxy average {oem_avg:.1f}%", f"Gap {gap:.1f} pts"],
    )


def _signal_component(signals: list[Signal], category: str, weight_key: str, explanation: str) -> ComponentScore:
    relevant = [signal for signal in signals if signal.category == category]
    if not relevant:
        return ComponentScore(weight_key, None, WEIGHTS[weight_key], "unavailable", f"No {category} evidence found in current filings.", [])
    higher = sum(signal.direction == "higher_commoditization" for signal in relevant)
    lower = sum(signal.direction == "lower_commoditization" for signal in relevant)
    score = _clamp(50 + 15 * higher - 15 * lower)
    return ComponentScore(
        weight_key,
        round(score, 1),
        WEIGHTS[weight_key],
        "low" if len(relevant) == 1 else "medium",
        explanation,
        [signal.evidence for signal in relevant[:5]],
    )


def calculate_score(metrics: list[Metric], signals: list[Signal]) -> ScoreResult:
    components = [
        _oem_margin_score(metrics),
        _value_capture_score(metrics),
        _signal_component(
            [signal for signal in signals if signal.company == "dell"],
            "attach",
            "dell_attach",
            "Explicit Dell-IP storage/network/services pull-through lowers commoditization risk; weak or absent attach evidence is left unscored rather than guessed.",
        ),
        _signal_component(
            signals,
            "pricing",
            "pricing_intensity",
            "More competitive-pricing language implies rising commoditization pressure.",
        ),
        ComponentScore(
            "architecture_convergence",
            None,
            WEIGHTS["architecture_convergence"],
            "unavailable",
            "SEC-only v1 does not infer architecture convergence from product pages. Add a separate public-product-source collector later.",
            [],
        ),
        _signal_component(
            signals,
            "supply",
            "supply_normalization",
            "Normalized supply and lead times reduce scarcity-based OEM differentiation; persistent constraints reduce the score.",
        ),
    ]

    available = [component for component in components if component.score is not None]
    available_weight = sum(component.weight for component in available)
    if not available or available_weight == 0:
        return ScoreResult(None, "unavailable", components, 0.0)
    weighted = sum(component.score * component.weight for component in available if component.score is not None) / available_weight
    coverage = available_weight / sum(WEIGHTS.values())
    confidence = "high" if coverage >= 0.8 else "medium" if coverage >= 0.55 else "low"
    return ScoreResult(round(weighted, 1), confidence, components, round(available_weight, 2))
