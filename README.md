# AI Server Commoditization Monitor

A small, auditable GitHub Actions monitor for one question:

> Is the AI-server hardware layer becoming commoditized, and where is the economic value moving?

It tracks **Dell Technologies, NVIDIA, Hewlett Packard Enterprise, and Super Micro Computer** using official SEC filings and attached earnings releases. The score is deterministic. Missing data stays missing.

## What v1 does

1. Checks SEC EDGAR once a week for each company's latest earnings filing.
2. Treats an 8-K containing Item 2.02 as the preferred earnings trigger, with 10-Q/10-K as a conservative fallback.
3. On the first live run, saves the four current filing accession numbers as the baseline and generates no report.
4. On later runs, waits until **all four companies** have a newer earnings filing than the baseline used for the previous completed cycle.
5. Pulls Exhibit 99.1 when available, otherwise the primary filing document.
6. Extracts selected metrics and qualitative signals without guessing unavailable values.
7. Calculates a 0-100 **AI Server Commoditization Index**.
8. Writes a Markdown report under `reports/`, appends structured history, advances the baseline, and opens a GitHub Issue.

## Why the cycle is accession-based

Dell, NVIDIA, HPE, and Supermicro use different fiscal calendars. Calling all of them "2026 Q3" creates false alignment. This project instead defines a completed monitoring cycle as: **each of the four companies has published at least one newer earnings filing since the previous completed report**.

## Index

- **0-25:** strongly differentiated
- **26-40:** differentiated
- **41-60:** moderate commoditization
- **61-75:** materially commoditized
- **76-100:** heavily commoditized

### v1 component weights

| Component | Weight | Public-data proxy |
|---|---:|---|
| OEM margin pressure | 30% | Dell ISG operating margin, SMCI gross margin, HPE Cloud & AI margin when extractable |
| NVIDIA vs OEM value-capture gap | 20% | NVIDIA gross margin minus available OEM margin proxies |
| Dell-IP attach | 15% | Explicit storage/network/services/pull-through language |
| Pricing intensity | 15% | Explicit competitive-pricing / pricing-pressure language |
| Architecture convergence | 10% | **Unscored in SEC-only v1** |
| Supply normalization | 10% | Explicit supply/lead-time normalization or constraint language |

If a component is unavailable, its weight is removed and available weights are re-normalized. Reports display scored-weight coverage and confidence.

### Important limitation

Accounting measures across companies are not perfectly comparable. NVIDIA gross margin, SMCI gross margin, and Dell/HPE segment operating margins are used as directional value-capture proxies, not apples-to-apples accounting metrics.

Architecture convergence also should not be inferred from SEC earnings filings. A later version should collect official Dell/HPE/SMCI/Lenovo/NVIDIA product specifications separately before enabling that 10% component.

## Repository layout

```text
.github/workflows/monitor.yml
AGENTS.md
README.md
pyproject.toml
src/ai_server_tracker/
  companies.py
  sec_client.py
  filings.py
  extract.py
  scoring.py
  report.py
  main.py
data/
  state.json
  history.json
reports/
tests/
```

## Required setup

GitHub Actions needs one repository secret because the SEC requests a descriptive `User-Agent` with contact information.

Go to:

**Settings → Secrets and variables → Actions → New repository secret**

Name:

```text
SEC_USER_AGENT
```

Value example:

```text
ai-server-commoditization your-email@example.com
```

Use an address you control. The workflow does not print the value.

## Run manually

After creating the secret:

**Actions → AI Server Commoditization Monitor → Run workflow**

The expected first-run result is:

```text
Baseline established. No report generated on first run.
```

The workflow then commits `data/state.json`. Future weekly runs remain quiet until all four issuers have reported newer earnings filings.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest

export SEC_USER_AGENT="ai-server-commoditization your-email@example.com"
python -m ai_server_tracker.main --verbose
```

## Design rules

- SEC / official earnings documents first.
- Never convert missing data into zero.
- Every metric retains evidence and source metadata.
- No report from a partial earnings cycle.
- No weekly state churn when nothing changed.
- Index calculation stays deterministic even if an LLM commentary layer is added later.

## Next useful upgrades

1. Add official product-page collection to score architecture/configuration convergence.
2. Add period-over-period metric deltas using the accumulated history.
3. Add a deterministic Dell attach-rate proxy from storage/network/services disclosures.
4. Add optional LLM commentary over verified facts while keeping scoring in code.
