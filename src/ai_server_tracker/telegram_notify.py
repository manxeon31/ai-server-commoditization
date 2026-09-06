from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HISTORY = ROOT / "data" / "history.json"


def _fmt_delta(current: float | None, previous: float | None) -> str:
    if current is None or previous is None:
        return "first scored cycle"
    delta = round(current - previous, 1)
    if delta > 0:
        return f"↑ {delta:.1f} vs prior"
    if delta < 0:
        return f"↓ {abs(delta):.1f} vs prior"
    return "unchanged vs prior"


def build_message(history: list[dict], report_url: str) -> str:
    if not history:
        raise ValueError("history is empty; no completed report is available")

    latest = history[-1]
    previous = history[-2] if len(history) > 1 else None
    score = latest.get("score", {})
    current = score.get("overall_score")
    previous_score = previous.get("score", {}).get("overall_score") if previous else None
    confidence = score.get("confidence", "unavailable")

    components = [
        component
        for component in score.get("components", [])
        if component.get("score") is not None
    ]
    components.sort(key=lambda component: component["score"], reverse=True)

    lines = [
        "[AI Server Commoditization]",
        "New complete earnings cycle detected: Dell + NVIDIA + HPE + Supermicro",
        "",
        f"Index: {'N/A' if current is None else f'{current:.1f}/100'}",
        f"Change: {_fmt_delta(current, previous_score)}",
        f"Confidence: {confidence}",
    ]

    if components:
        lines.extend(["", "Top commoditization pressures:"])
        for component in components[:3]:
            label = component.get("category", "unknown").replace("_", " ").title()
            lines.append(f"• {label}: {component['score']:.1f}/100")

    lines.extend(["", f"Full report: {report_url}"])
    return "\n".join(lines)


def send_telegram(message: str, token: str, chat_id: str, timeout: float = 20.0) -> None:
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message, "disable_web_page_preview": True},
        timeout=timeout,
    )
    response.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser(description="Send the latest AI-server commoditization report to Telegram.")
    parser.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument("--report-url", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    history = json.loads(args.history.read_text(encoding="utf-8"))
    message = build_message(history, args.report_url)

    if args.dry_run:
        print(message)
        return 0

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise SystemExit("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required for Telegram delivery.")

    send_telegram(message, token, chat_id)
    print("Telegram notification sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
