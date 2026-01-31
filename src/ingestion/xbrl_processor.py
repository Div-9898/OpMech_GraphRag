"""XBRL processor for extracting financial line items from SEC filings."""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import requests
from loguru import logger

from src.config import settings
from src.models import Node, NodeMetadata, NodeType


class XBRLProcessor:
    """Processes XBRL data to extract financial line items."""

    # Common US GAAP tags we want to extract
    IMPORTANT_TAGS = {
        # Income Statement
        "us-gaap:Revenues": "Total Revenue",
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax": "Net Sales",
        "us-gaap:CostOfGoodsAndServicesSold": "Cost of Sales",
        "us-gaap:GrossProfit": "Gross Profit",
        "us-gaap:OperatingExpenses": "Operating Expenses",
        "us-gaap:ResearchAndDevelopmentExpense": "R&D Expense",
        "us-gaap:SellingGeneralAndAdministrativeExpense": "SG&A Expense",
        "us-gaap:OperatingIncomeLoss": "Operating Income",
        "us-gaap:InterestExpense": "Interest Expense",
        "us-gaap:IncomeTaxExpenseBenefit": "Income Tax Expense",
        "us-gaap:NetIncomeLoss": "Net Income",
        "us-gaap:EarningsPerShareBasic": "EPS Basic",
        "us-gaap:EarningsPerShareDiluted": "EPS Diluted",
        # Balance Sheet
        "us-gaap:Assets": "Total Assets",
        "us-gaap:AssetsCurrent": "Current Assets",
        "us-gaap:CashAndCashEquivalentsAtCarryingValue": "Cash and Equivalents",
        "us-gaap:MarketableSecuritiesCurrent": "Marketable Securities",
        "us-gaap:AccountsReceivableNetCurrent": "Accounts Receivable",
        "us-gaap:InventoryNet": "Inventory",
        "us-gaap:PropertyPlantAndEquipmentNet": "Property Plant Equipment",
        "us-gaap:Goodwill": "Goodwill",
        "us-gaap:Liabilities": "Total Liabilities",
        "us-gaap:LiabilitiesCurrent": "Current Liabilities",
        "us-gaap:AccountsPayableCurrent": "Accounts Payable",
        "us-gaap:LongTermDebt": "Long-term Debt",
        "us-gaap:StockholdersEquity": "Stockholders Equity",
        "us-gaap:RetainedEarningsAccumulatedDeficit": "Retained Earnings",
        # Cash Flow
        "us-gaap:NetCashProvidedByUsedInOperatingActivities": "Cash from Operations",
        "us-gaap:NetCashProvidedByUsedInInvestingActivities": "Cash from Investing",
        "us-gaap:NetCashProvidedByUsedInFinancingActivities": "Cash from Financing",
        "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment": "CapEx",
        "us-gaap:PaymentsForRepurchaseOfCommonStock": "Stock Repurchases",
        "us-gaap:PaymentsOfDividends": "Dividends Paid",
    }

    def __init__(self, filing_id: str, period: str):
        self.filing_id = filing_id
        self.period = period
        self.node_counter = 0

    def _generate_node_id(self) -> str:
        """Generate a unique node ID for financial line items."""
        self.node_counter += 1
        return f"{self.filing_id}_FL_{self.node_counter:04d}"

    def process_company_facts(self, company_facts: dict) -> list[Node]:
        """
        Process XBRL company facts API response.

        Args:
            company_facts: Response from SEC's companyfacts API

        Returns:
            List of Node objects for financial line items
        """
        nodes = []

        facts = company_facts.get("facts", {})

        # Process US-GAAP facts
        us_gaap = facts.get("us-gaap", {})

        for tag_short, description in self.IMPORTANT_TAGS.items():
            # Remove namespace prefix for lookup
            tag_name = tag_short.split(":")[-1]

            if tag_name not in us_gaap:
                continue

            tag_data = us_gaap[tag_name]
            units = tag_data.get("units", {})

            # Get the appropriate unit (USD for monetary, pure for ratios)
            unit_data = units.get("USD") or units.get("USD/shares") or units.get("shares") or list(units.values())[0] if units else []

            for fact in unit_data:
                # Filter to our target periods
                period_end = fact.get("end", "")
                fiscal_year = fact.get("fy")
                fiscal_period = fact.get("fp", "")

                # Determine if this fact is in our target range
                target_period = self._match_period(fiscal_year, fiscal_period, period_end)
                if not target_period:
                    continue

                # Skip if not matching our filing's period
                if target_period != self.period:
                    continue

                value = fact.get("val")
                if value is None:
                    continue

                # Create text representation
                unit_str = "USD" if "USD" in str(units.keys()) else fact.get("unit", "")
                if abs(value) >= 1_000_000_000:
                    value_str = f"${value / 1_000_000_000:.2f}B"
                elif abs(value) >= 1_000_000:
                    value_str = f"${value / 1_000_000:.2f}M"
                else:
                    value_str = f"${value:,.2f}" if "USD" in unit_str else f"{value:,.2f}"

                text = f"{description}: {value_str} ({period_end})"

                node = Node(
                    id=self._generate_node_id(),
                    type=NodeType.FINANCIAL_LINE,
                    text=text,
                    metadata=NodeMetadata(
                        filing_id=self.filing_id,
                        period=self.period,
                        xbrl_tag=tag_short,
                        value=float(value),
                        unit=unit_str,
                    ),
                )
                nodes.append(node)

        logger.info(f"Extracted {len(nodes)} financial line items for {self.period}")
        return nodes

    def _match_period(self, fiscal_year: int, fiscal_period: str, period_end: str) -> str | None:
        """Match XBRL period data to our filing period format."""
        if not fiscal_year:
            return None

        if fiscal_period == "FY":
            return f"FY{fiscal_year}"
        elif fiscal_period in ["Q1", "Q2", "Q3"]:
            return f"{fiscal_period}-{fiscal_year}"

        return None

    def process_xbrl_file(self, xbrl_path: Path) -> list[Node]:
        """
        Process a local XBRL file.

        This is a fallback when company facts API doesn't have the data.
        """
        nodes = []

        try:
            tree = ET.parse(xbrl_path)
            root = tree.getroot()

            # Define namespaces
            namespaces = {
                "us-gaap": "http://fasb.org/us-gaap/2023",
                "dei": "http://xbrl.sec.gov/dei/2023",
            }

            # Try to extract facts
            for tag_full, description in self.IMPORTANT_TAGS.items():
                ns, tag = tag_full.split(":")
                elements = root.findall(f".//{{{namespaces.get(ns, '')}}}{tag}")

                for elem in elements:
                    value_text = elem.text
                    if not value_text:
                        continue

                    try:
                        value = float(value_text.replace(",", ""))
                    except ValueError:
                        continue

                    # Get context for period info
                    context_ref = elem.get("contextRef", "")

                    text = f"{description}: {value:,.2f}"

                    node = Node(
                        id=self._generate_node_id(),
                        type=NodeType.FINANCIAL_LINE,
                        text=text,
                        metadata=NodeMetadata(
                            filing_id=self.filing_id,
                            period=self.period,
                            xbrl_tag=tag_full,
                            value=value,
                            unit="USD",
                        ),
                    )
                    nodes.append(node)

        except Exception as e:
            logger.warning(f"Error parsing XBRL file: {e}")

        return nodes


def fetch_and_process_company_facts(filing_id: str, period: str) -> list[Node]:
    """Fetch company facts from SEC API and process them."""
    processor = XBRLProcessor(filing_id, period)

    url = f"{settings.sec_base_url}/api/xbrl/companyfacts/CIK{settings.apple_cik}.json"
    headers = {"User-Agent": settings.sec_user_agent}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        company_facts = response.json()

        # Cache the response
        cache_path = settings.raw_dir / "company_facts.json"
        cache_path.write_text(json.dumps(company_facts, indent=2))

        return processor.process_company_facts(company_facts)

    except Exception as e:
        logger.error(f"Error fetching company facts: {e}")

        # Try to load from cache
        cache_path = settings.raw_dir / "company_facts.json"
        if cache_path.exists():
            logger.info("Loading company facts from cache")
            company_facts = json.loads(cache_path.read_text())
            return processor.process_company_facts(company_facts)

        return []


if __name__ == "__main__":
    import sys
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # Test fetching company facts
    settings.ensure_dirs()
    nodes = fetch_and_process_company_facts("AAPL-10K-2024", "FY2024")
    logger.info(f"Extracted {len(nodes)} financial line items")

    for node in nodes[:10]:
        logger.info(f"  {node.metadata.xbrl_tag}: {node.text}")
