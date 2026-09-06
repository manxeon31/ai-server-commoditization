from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOGGER = logging.getLogger(__name__)


class SecClientError(RuntimeError):
    pass


@dataclass
class SecClient:
    user_agent: str
    timeout_seconds: float = 20.0

    def __post_init__(self) -> None:
        if not self.user_agent.strip():
            raise ValueError("SEC user agent is required")
        self.session = requests.Session()
        retry = Retry(
            total=4,
            connect=4,
            read=4,
            backoff_factor=0.8,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Host": "data.sec.gov",
            }
        )

    def _get(self, url: str) -> requests.Response:
        # Host differs for archive documents, so avoid a fixed Host header.
        headers = dict(self.session.headers)
        headers.pop("Host", None)
        try:
            response = self.session.get(url, headers=headers, timeout=self.timeout_seconds)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise SecClientError(f"SEC request failed for {url}: {exc}") from exc

    def get_json(self, url: str) -> dict:
        response = self._get(url)
        try:
            return response.json()
        except ValueError as exc:
            raise SecClientError(f"SEC returned invalid JSON for {url}") from exc

    def get_text(self, url: str) -> str:
        return self._get(url).text

    def get_submissions(self, cik: int) -> dict:
        return self.get_json(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")

    @staticmethod
    def accession_folder(accession: str) -> str:
        return accession.replace("-", "")

    @classmethod
    def filing_base_url(cls, cik: int, accession: str) -> str:
        return (
            f"https://www.sec.gov/Archives/edgar/data/{cik}/"
            f"{cls.accession_folder(accession)}/"
        )

    @classmethod
    def primary_document_url(cls, cik: int, accession: str, primary_document: str) -> str:
        return urljoin(cls.filing_base_url(cik, accession), primary_document)

    @classmethod
    def filing_index_url(cls, cik: int, accession: str) -> str:
        return urljoin(cls.filing_base_url(cik, accession), f"{accession}-index.html")

    def find_exhibit_99_1_url(self, cik: int, accession: str) -> str | None:
        index_url = self.filing_index_url(cik, accession)
        html = self.get_text(index_url)
        soup = BeautifulSoup(html, "html.parser")
        for row in soup.select("table.tableFile tr"):
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            filing_type = cells[3].get_text(" ", strip=True).upper()
            if filing_type in {"EX-99.1", "EX-99.01"}:
                link = cells[2].find("a")
                if link and link.get("href"):
                    return urljoin("https://www.sec.gov", link["href"])
        return None

    def get_earnings_document(
        self,
        cik: int,
        accession: str,
        primary_document: str,
    ) -> tuple[str, str]:
        try:
            exhibit_url = self.find_exhibit_99_1_url(cik, accession)
        except SecClientError:
            LOGGER.warning("Could not inspect filing index for %s; using primary document", accession)
            exhibit_url = None
        url = exhibit_url or self.primary_document_url(cik, accession, primary_document)
        return url, self.get_text(url)
