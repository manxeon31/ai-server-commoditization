from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompanyConfig:
    key: str
    name: str
    ticker: str
    cik: int


COMPANIES: tuple[CompanyConfig, ...] = (
    CompanyConfig("dell", "Dell Technologies Inc.", "DELL", 1571996),
    CompanyConfig("nvidia", "NVIDIA Corporation", "NVDA", 1045810),
    CompanyConfig("hpe", "Hewlett Packard Enterprise Company", "HPE", 1645590),
    CompanyConfig("smci", "Super Micro Computer, Inc.", "SMCI", 1375365),
)

COMPANY_BY_KEY = {company.key: company for company in COMPANIES}
