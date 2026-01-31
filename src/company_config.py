"""
Company-Agnostic Configuration Module.

Auto-detects company information from loaded SEC documents.
Replaces all hardcoded Apple-specific values.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from pathlib import Path
from loguru import logger


@dataclass
class CompanyConfig:
    """
    Company configuration that auto-populates from loaded documents.

    Usage:
        # From ticker symbol (uses SEC EDGAR API):
        config = CompanyConfig.from_ticker("AAPL")

        # From CIK:
        config = CompanyConfig.from_cik("0000320193")

        # From loaded documents (auto-detect):
        config = CompanyConfig.from_documents(documents)
    """

    # Core identifiers
    name: str = ""
    ticker: str = ""
    cik: str = ""

    # Fiscal configuration (auto-detected)
    fiscal_year_end_month: int = 12  # Default December, auto-detected from docs

    # Business segments (extracted from documents)
    segments: List[str] = field(default_factory=list)
    products: List[str] = field(default_factory=list)
    geographic_regions: List[str] = field(default_factory=list)

    # XBRL tags found in documents (for dynamic ground truth)
    xbrl_tags: Dict[str, str] = field(default_factory=dict)  # tag -> description

    # Metadata
    sic_code: str = ""
    industry: str = ""

    @classmethod
    def from_ticker(cls, ticker: str) -> "CompanyConfig":
        """
        Create config from ticker symbol using SEC EDGAR API.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL", "MSFT", "GOOGL")

        Returns:
            CompanyConfig with CIK and company name populated
        """
        import requests
        from src.config import settings

        ticker = ticker.upper().strip()

        # Use SEC EDGAR company tickers endpoint
        headers = {"User-Agent": settings.sec_user_agent}

        try:
            # Method 1: Company tickers JSON (most reliable)
            url = "https://www.sec.gov/files/company_tickers.json"
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Search for ticker
            for entry in data.values():
                if entry.get("ticker", "").upper() == ticker:
                    cik = str(entry.get("cik_str", "")).zfill(10)
                    name = entry.get("title", "")

                    config = cls(
                        name=name,
                        ticker=ticker,
                        cik=cik,
                    )
                    logger.info(f"Found company: {name} (CIK: {cik}) for ticker {ticker}")
                    return config

            raise ValueError(f"Ticker '{ticker}' not found in SEC database")

        except requests.RequestException as e:
            logger.error(f"Failed to lookup ticker {ticker}: {e}")
            raise ValueError(f"Could not lookup ticker '{ticker}': {e}")

    @classmethod
    def from_cik(cls, cik: str) -> "CompanyConfig":
        """
        Create config from CIK using SEC EDGAR API.

        Args:
            cik: SEC Central Index Key (e.g., "0000320193")

        Returns:
            CompanyConfig with company name and ticker populated
        """
        import requests
        from src.config import settings

        # Normalize CIK to 10 digits
        cik = str(cik).zfill(10)

        headers = {"User-Agent": settings.sec_user_agent}

        try:
            # Get company submissions data
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            name = data.get("name", "")
            tickers = data.get("tickers", [])
            ticker = tickers[0] if tickers else ""
            sic = data.get("sic", "")
            sic_description = data.get("sicDescription", "")
            fiscal_year_end = data.get("fiscalYearEnd", "1231")  # MMDD format

            # Parse fiscal year end month
            fiscal_month = int(fiscal_year_end[:2]) if len(fiscal_year_end) >= 2 else 12

            config = cls(
                name=name,
                ticker=ticker,
                cik=cik,
                fiscal_year_end_month=fiscal_month,
                sic_code=sic,
                industry=sic_description,
            )
            logger.info(f"Found company: {name} (ticker: {ticker}) for CIK {cik}")
            return config

        except requests.RequestException as e:
            logger.error(f"Failed to lookup CIK {cik}: {e}")
            raise ValueError(f"Could not lookup CIK '{cik}': {e}")

    @classmethod
    def from_documents(cls, documents: List[Dict]) -> "CompanyConfig":
        """
        Auto-detect company configuration from loaded documents.

        Args:
            documents: List of parsed document dicts with metadata

        Returns:
            CompanyConfig populated from document analysis
        """
        config = cls()

        if not documents:
            logger.warning("No documents provided for config extraction")
            return config

        # Extract from first document with metadata
        for doc in documents:
            metadata = doc.get("metadata", {})

            # Try to get CIK from metadata
            if not config.cik and metadata.get("cik"):
                config.cik = str(metadata["cik"]).zfill(10)

            # Try to get company name
            if not config.name and metadata.get("company_name"):
                config.name = metadata["company_name"]

            # Try to get ticker
            if not config.ticker and metadata.get("ticker"):
                config.ticker = metadata["ticker"]

            # Detect fiscal year end from period dates
            if config.fiscal_year_end_month == 12:  # Still default
                period_end = metadata.get("period_end_date", metadata.get("fiscal_year_end", ""))
                if period_end:
                    detected_month = cls._detect_fiscal_month(period_end)
                    if detected_month:
                        config.fiscal_year_end_month = detected_month

        # Extract segments, products, regions from document content
        config._extract_business_info_from_documents(documents)

        # Extract XBRL tags
        config._extract_xbrl_tags_from_documents(documents)

        # If we have CIK but missing name/ticker, fetch from SEC
        if config.cik and (not config.name or not config.ticker):
            try:
                fetched = cls.from_cik(config.cik)
                if not config.name:
                    config.name = fetched.name
                if not config.ticker:
                    config.ticker = fetched.ticker
            except Exception as e:
                logger.warning(f"Could not fetch additional info from SEC: {e}")

        return config

    @staticmethod
    def _detect_fiscal_month(date_str: str) -> Optional[int]:
        """Detect fiscal year end month from a date string."""
        import re
        from datetime import datetime

        # Try various date formats
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.month
            except ValueError:
                continue

        # Try regex for YYYY-MM-DD
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_str)
        if match:
            return int(match.group(2))

        return None

    def _extract_business_info_from_documents(self, documents: List[Dict]) -> None:
        """Extract segments, products, and regions from document content."""

        all_text = ""
        for doc in documents:
            content = doc.get("content", doc.get("text", ""))
            if isinstance(content, str):
                all_text += " " + content
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        all_text += " " + item.get("text", "")
                    elif isinstance(item, str):
                        all_text += " " + item

        if not all_text:
            return

        # Extract segments from common patterns
        self.segments = self._extract_segments(all_text)
        self.products = self._extract_products(all_text)
        self.geographic_regions = self._extract_regions(all_text)

    def _extract_segments(self, text: str) -> List[str]:
        """Extract business segments from document text."""
        segments = set()

        # Look for "reportable segment" patterns
        segment_patterns = [
            r'reportable\s+(?:operating\s+)?segments?\s*(?:are|include|:)?\s*([^.]+)',
            r'(?:our|the)\s+(?:operating\s+)?segments?\s*(?:are|include|:)\s*([^.]+)',
            r'segment\s+(?:information|reporting).*?(?:segments?\s+(?:are|include|:))\s*([^.]+)',
        ]

        for pattern in segment_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Split by common delimiters
                parts = re.split(r'[,;]|\band\b', match)
                for part in parts:
                    clean = part.strip().strip('.')
                    if clean and len(clean) > 2 and len(clean) < 50:
                        segments.add(clean)

        return list(segments)[:10]  # Limit to 10 segments

    def _extract_products(self, text: str) -> List[str]:
        """Extract product lines from document text."""
        products = set()

        # Look for product revenue patterns
        product_patterns = [
            r'(?:products?\s+(?:and\s+)?services?\s+include|our\s+products?\s+include|product\s+(?:lines?|categories?)\s*:)\s*([^.]+)',
            r'revenue\s+(?:from|by)\s+(?:product|category).*?(?:include|:)\s*([^.]+)',
        ]

        for pattern in product_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                parts = re.split(r'[,;]|\band\b', match)
                for part in parts:
                    clean = part.strip().strip('.')
                    if clean and len(clean) > 2 and len(clean) < 40:
                        products.add(clean)

        return list(products)[:15]  # Limit to 15 products

    def _extract_regions(self, text: str) -> List[str]:
        """Extract geographic regions from document text."""
        regions = set()

        # Common geographic patterns
        region_patterns = [
            r'(?:geographic\s+)?(?:regions?|areas?)\s*(?:include|:)\s*([^.]+)',
            r'(?:Americas?|Europe|Asia|APAC|EMEA|Greater\s+China|Japan)',
        ]

        # Standard regions to look for
        standard_regions = [
            "Americas", "North America", "United States", "U.S.",
            "Europe", "EMEA", "European Union",
            "Asia Pacific", "APAC", "Greater China", "China",
            "Japan", "Rest of Asia Pacific",
            "Other Countries", "International",
        ]

        for region in standard_regions:
            if re.search(r'\b' + re.escape(region) + r'\b', text, re.IGNORECASE):
                regions.add(region)

        return list(regions)[:10]

    def _extract_xbrl_tags_from_documents(self, documents: List[Dict]) -> None:
        """Extract XBRL tags found in documents."""
        for doc in documents:
            # Look for XBRL nodes
            nodes = doc.get("nodes", doc.get("xbrl_nodes", []))
            for node in nodes:
                if isinstance(node, dict):
                    tag = node.get("xbrl_tag", node.get("tag", ""))
                    label = node.get("label", node.get("description", tag))
                    if tag and tag not in self.xbrl_tags:
                        self.xbrl_tags[tag] = label

    def get_filing_id_prefix(self) -> str:
        """Get the prefix for filing IDs (e.g., 'AAPL' or 'MSFT')."""
        if self.ticker:
            return self.ticker.upper()
        elif self.name:
            # Use first word of company name
            return re.sub(r'[^A-Z]', '', self.name.upper())[:4]
        elif self.cik:
            return f"CIK{self.cik[-6:]}"
        return "COMPANY"

    def format_fiscal_period(self, period_end_date: str, filing_type: str) -> str:
        """
        Format a fiscal period label based on this company's fiscal year.

        Args:
            period_end_date: Period end date (YYYY-MM-DD)
            filing_type: "10-K" or "10-Q"

        Returns:
            Formatted period label (e.g., "FY2024", "Q1-FY2024")
        """
        from datetime import datetime

        # Parse the date
        try:
            if isinstance(period_end_date, str):
                dt = datetime.strptime(period_end_date[:10], "%Y-%m-%d")
            else:
                dt = period_end_date
        except ValueError:
            return f"FY{period_end_date[:4]}" if period_end_date else "FY????"

        # Determine fiscal year
        if dt.month <= self.fiscal_year_end_month:
            fiscal_year = dt.year
        else:
            fiscal_year = dt.year + 1

        if filing_type == "10-K":
            return f"FY{fiscal_year}"
        else:
            # Determine quarter based on months since fiscal year start
            fiscal_start_month = (self.fiscal_year_end_month % 12) + 1

            months_into_fy = (dt.month - fiscal_start_month) % 12
            quarter = (months_into_fy // 3) + 1

            return f"Q{quarter}-FY{fiscal_year}"

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "ticker": self.ticker,
            "cik": self.cik,
            "fiscal_year_end_month": self.fiscal_year_end_month,
            "segments": self.segments,
            "products": self.products,
            "geographic_regions": self.geographic_regions,
            "sic_code": self.sic_code,
            "industry": self.industry,
            "xbrl_tags": self.xbrl_tags,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CompanyConfig":
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            ticker=data.get("ticker", ""),
            cik=data.get("cik", ""),
            fiscal_year_end_month=data.get("fiscal_year_end_month", 12),
            segments=data.get("segments", []),
            products=data.get("products", []),
            geographic_regions=data.get("geographic_regions", []),
            sic_code=data.get("sic_code", ""),
            industry=data.get("industry", ""),
            xbrl_tags=data.get("xbrl_tags", {}),
        )

    def __str__(self) -> str:
        return f"CompanyConfig({self.ticker or self.cik}: {self.name})"

    def __repr__(self) -> str:
        return (
            f"CompanyConfig(name='{self.name}', ticker='{self.ticker}', "
            f"cik='{self.cik}', fiscal_year_end_month={self.fiscal_year_end_month})"
        )


# Global instance that can be set once and used throughout
_active_config: Optional[CompanyConfig] = None


def set_active_company(config: CompanyConfig) -> None:
    """Set the active company configuration for the session."""
    global _active_config
    _active_config = config
    logger.info(f"Active company set to: {config}")


def get_active_company() -> Optional[CompanyConfig]:
    """Get the active company configuration."""
    return _active_config


def require_active_company() -> CompanyConfig:
    """Get the active company configuration, raising if not set."""
    if _active_config is None:
        raise RuntimeError(
            "No active company configuration. "
            "Call set_active_company() first or use CompanyConfig.from_ticker()."
        )
    return _active_config
