"""SEC EDGAR API client for fetching company filings (company-agnostic)."""

import json
import time
from pathlib import Path
from typing import Generator, List, Optional, Tuple

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models import Filing
from src.company_config import CompanyConfig, get_active_company


class SECFetcher:
    """
    Fetches SEC filings from EDGAR API.

    COMPANY-AGNOSTIC: Works with any company via CompanyConfig.
    """

    def __init__(self, company_config: Optional[CompanyConfig] = None):
        """
        Initialize the SEC fetcher.

        Args:
            company_config: Company configuration. If not provided, uses active company.
        """
        self.base_url = settings.sec_base_url
        self.rate_limit = settings.sec_rate_limit
        self.last_request_time = 0.0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": settings.sec_user_agent,
            "Accept": "application/json",
        })

        # Use provided config or get active company
        self._company_config = company_config

    @property
    def company_config(self) -> CompanyConfig:
        """Get the company configuration."""
        if self._company_config is not None:
            return self._company_config

        active = get_active_company()
        if active is not None:
            return active

        raise ValueError(
            "No company configuration provided. "
            "Either pass a CompanyConfig to __init__ or call set_active_company() first."
        )

    @property
    def cik(self) -> str:
        """Get the CIK from company config."""
        return self.company_config.cik

    def _rate_limit_wait(self) -> None:
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        min_interval = 1.0 / self.rate_limit
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self.last_request_time = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=8),
    )
    def _get(self, url: str) -> requests.Response:
        """Make a rate-limited GET request with retry logic."""
        self._rate_limit_wait()
        logger.debug(f"Fetching: {url}")
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response

    @classmethod
    def from_ticker(cls, ticker: str) -> "SECFetcher":
        """
        Create a fetcher for a company by ticker symbol.

        Args:
            ticker: Stock ticker (e.g., "AAPL", "MSFT", "GOOGL")

        Returns:
            SECFetcher configured for that company
        """
        config = CompanyConfig.from_ticker(ticker)
        return cls(company_config=config)

    @classmethod
    def from_cik(cls, cik: str) -> "SECFetcher":
        """
        Create a fetcher for a company by CIK.

        Args:
            cik: SEC Central Index Key

        Returns:
            SECFetcher configured for that company
        """
        config = CompanyConfig.from_cik(cik)
        return cls(company_config=config)

    def get_company_filings(self) -> dict:
        """Get the filings index for the company."""
        cik = self.cik.zfill(10)
        url = f"{self.base_url}/submissions/CIK{cik}.json"
        response = self._get(url)
        return response.json()

    def get_filing_list(self, filing_type: Optional[str] = None) -> List[Filing]:
        """Get list of filings, optionally filtered by type."""
        data = self.get_company_filings()

        filings = []
        recent = data.get("filings", {}).get("recent", {})

        # Get all arrays
        accession_numbers = recent.get("accessionNumber", [])
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        primary_documents = recent.get("primaryDocument", [])

        # Get company info from data
        company_name = data.get("name", self.company_config.name)
        cik = self.cik.zfill(10)

        for i in range(len(accession_numbers)):
            form = forms[i]

            # Filter by type if specified
            if filing_type and form != filing_type:
                continue

            # Only include 10-K and 10-Q
            if form not in ["10-K", "10-Q"]:
                continue

            accession = accession_numbers[i].replace("-", "")
            filing = Filing(
                accession_number=accession_numbers[i],
                filing_type=form,
                filing_date=filing_dates[i],
                period=self._determine_period(form, filing_dates[i]),
                cik=cik,
                company_name=company_name,
                document_url=f"{settings.sec_archive_url}/Archives/edgar/data/{cik}/{accession}/{primary_documents[i]}",
            )
            filings.append(filing)

        return filings

    def _determine_period(self, filing_type: str, filing_date: str) -> str:
        """
        Determine the fiscal period based on filing type and date.

        Uses company's fiscal year end month for accurate period labels.
        """
        year = int(filing_date[:4])
        month = int(filing_date[5:7])

        # Get fiscal year end month from company config
        fy_end_month = self.company_config.fiscal_year_end_month

        if filing_type == "10-K":
            # 10-K is filed after fiscal year ends
            # If filed in months 1-3 after FY end, it's for that FY
            if fy_end_month == 12:
                # Calendar year company
                if month in [1, 2, 3]:
                    return f"FY{year - 1}"
                else:
                    return f"FY{year}"
            else:
                # Non-calendar fiscal year
                if month > fy_end_month:
                    return f"FY{year}"
                else:
                    return f"FY{year - 1}"
        else:  # 10-Q
            # Determine quarter based on filing month relative to fiscal year
            fiscal_start_month = (fy_end_month % 12) + 1

            # Calculate months into fiscal year
            if month >= fiscal_start_month:
                months_into_fy = month - fiscal_start_month
                fiscal_year = year + (1 if fy_end_month < 12 else 0)
            else:
                months_into_fy = (12 - fiscal_start_month) + month
                fiscal_year = year

            # Typical filing delay is ~45 days, so Q1 filed in Jan/Feb, etc.
            # Adjust for filing delay
            months_into_fy = max(0, months_into_fy - 1)

            quarter = min(3, (months_into_fy // 3) + 1)

            return f"Q{quarter}-{fiscal_year}"

    def get_filings_by_period(
        self,
        fiscal_years: Optional[List[int]] = None,
        include_10k: bool = True,
        include_10q: bool = True,
        num_years: int = 3,
    ) -> List[Filing]:
        """
        Get filings for specified periods.

        Args:
            fiscal_years: List of fiscal years to fetch. If None, gets most recent.
            include_10k: Include 10-K annual reports
            include_10q: Include 10-Q quarterly reports
            num_years: Number of years to fetch if fiscal_years not specified

        Returns:
            List of Filing objects for the requested periods
        """
        all_filings = self.get_filing_list()

        if fiscal_years is None:
            # Get most recent years
            years_found = set()
            for f in all_filings:
                if f.filing_type == "10-K":
                    year_match = f.period.replace("FY", "")
                    try:
                        years_found.add(int(year_match))
                    except ValueError:
                        continue

            if years_found:
                fiscal_years = sorted(years_found, reverse=True)[:num_years]
            else:
                return []

        # Build target periods
        target_periods_10k = {f"FY{y}" for y in fiscal_years} if include_10k else set()
        target_periods_10q = set()

        if include_10q:
            for y in fiscal_years:
                target_periods_10q.update([f"Q1-{y}", f"Q2-{y}", f"Q3-{y}"])

        # Filter filings
        result = []
        for filing in all_filings:
            if filing.filing_type == "10-K" and filing.period in target_periods_10k:
                result.append(filing)
                target_periods_10k.discard(filing.period)
            elif filing.filing_type == "10-Q" and filing.period in target_periods_10q:
                result.append(filing)
                target_periods_10q.discard(filing.period)

        logger.info(f"Found {len(result)} filings for {self.company_config.ticker or self.cik}")
        if target_periods_10k:
            logger.warning(f"Missing 10-K filings: {target_periods_10k}")
        if target_periods_10q:
            logger.warning(f"Missing 10-Q filings: {target_periods_10q}")

        return result

    # Backwards compatibility alias
    def get_target_filings(self) -> List[Filing]:
        """Get filings for the most recent 3 fiscal years."""
        return self.get_filings_by_period(num_years=3)

    def download_filing(self, filing: Filing, output_dir: Optional[Path] = None) -> Path:
        """Download a filing's primary document."""
        if output_dir is None:
            output_dir = settings.raw_dir

        cik = self.cik.zfill(10)

        # Create directory for this filing
        filing_dir = output_dir / cik / filing.accession_number.replace("-", "")
        filing_dir.mkdir(parents=True, exist_ok=True)

        # Download primary document
        doc_path = filing_dir / "filing.html"
        if not doc_path.exists():
            response = self._get(filing.document_url)
            doc_path.write_bytes(response.content)
            logger.info(f"Downloaded: {filing.filing_type} {filing.period} -> {doc_path}")
        else:
            logger.debug(f"Already cached: {doc_path}")

        # Save metadata
        meta_path = filing_dir / "metadata.json"
        if not meta_path.exists():
            meta_path.write_text(filing.model_dump_json(indent=2))

        return doc_path

    def download_xbrl(self, filing: Filing, output_dir: Optional[Path] = None) -> Optional[Path]:
        """Download XBRL data for a filing."""
        if output_dir is None:
            output_dir = settings.raw_dir

        cik = self.cik.zfill(10)

        filing_dir = output_dir / cik / filing.accession_number.replace("-", "")
        filing_dir.mkdir(parents=True, exist_ok=True)

        # Try to find XBRL files in the filing index
        accession = filing.accession_number.replace("-", "")
        index_url = f"{settings.sec_archive_url}/Archives/edgar/data/{cik}/{accession}/index.json"

        try:
            response = self._get(index_url)
            index_data = response.json()

            # Look for XBRL files
            for item in index_data.get("directory", {}).get("item", []):
                name = item.get("name", "")
                if name.endswith((".xml", "_htm.xml")) and "xbrl" in name.lower():
                    xbrl_url = f"{settings.sec_archive_url}/Archives/edgar/data/{cik}/{accession}/{name}"
                    xbrl_path = filing_dir / "filing_xbrl.xml"

                    if not xbrl_path.exists():
                        xbrl_response = self._get(xbrl_url)
                        xbrl_path.write_bytes(xbrl_response.content)
                        logger.info(f"Downloaded XBRL: {filing.period} -> {xbrl_path}")

                    return xbrl_path

        except Exception as e:
            logger.warning(f"Could not fetch XBRL for {filing.period}: {e}")

        return None

    def download_all_filings(
        self,
        fiscal_years: Optional[List[int]] = None,
        num_years: int = 3,
    ) -> List[Tuple[Filing, Path]]:
        """Download all target filings."""
        settings.ensure_dirs()
        filings = self.get_filings_by_period(fiscal_years=fiscal_years, num_years=num_years)

        results = []
        for filing in filings:
            try:
                doc_path = self.download_filing(filing)
                self.download_xbrl(filing)  # Best effort
                results.append((filing, doc_path))
            except Exception as e:
                logger.error(f"Failed to download {filing.filing_type} {filing.period}: {e}")

        logger.info(f"Downloaded {len(results)}/{len(filings)} filings")
        return results

    def get_xbrl_company_facts(self) -> dict:
        """Get XBRL company facts (all financial data)."""
        cik = self.cik.zfill(10)
        url = f"{self.base_url}/api/xbrl/companyfacts/CIK{cik}.json"
        response = self._get(url)
        return response.json()


def fetch_company_filings(
    ticker: Optional[str] = None,
    cik: Optional[str] = None,
    company_config: Optional[CompanyConfig] = None,
) -> List[Tuple[Filing, Path]]:
    """
    Convenience function to fetch filings for any company.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        cik: SEC CIK number
        company_config: Pre-built CompanyConfig

    Returns:
        List of (Filing, Path) tuples
    """
    if company_config:
        fetcher = SECFetcher(company_config=company_config)
    elif ticker:
        fetcher = SECFetcher.from_ticker(ticker)
    elif cik:
        fetcher = SECFetcher.from_cik(cik)
    else:
        raise ValueError("Must provide ticker, cik, or company_config")

    return fetcher.download_all_filings()


# Backwards compatibility
def fetch_apple_filings() -> List[Tuple[Filing, Path]]:
    """Fetch Apple filings (backwards compatibility)."""
    logger.warning(
        "fetch_apple_filings() is deprecated. "
        "Use fetch_company_filings(ticker='AAPL') instead."
    )
    return fetch_company_filings(ticker="AAPL")


if __name__ == "__main__":
    # Test the fetcher with any company
    import sys

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # Default to Apple if no argument
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"

    logger.info(f"Fetching filings for {ticker}...")
    fetcher = SECFetcher.from_ticker(ticker)

    logger.info(f"Company: {fetcher.company_config.name}")
    logger.info(f"CIK: {fetcher.company_config.cik}")
    logger.info(f"Fiscal Year End: Month {fetcher.company_config.fiscal_year_end_month}")

    # List available filings
    logger.info("Fetching filing list...")
    filings = fetcher.get_target_filings()
    for f in filings:
        logger.info(f"  {f.filing_type} {f.period} - {f.filing_date}")

    # Optionally download
    if len(sys.argv) > 2 and sys.argv[2] == "--download":
        logger.info("\nDownloading filings...")
        results = fetcher.download_all_filings()
        logger.info(f"\nCompleted: {len(results)} filings downloaded")
