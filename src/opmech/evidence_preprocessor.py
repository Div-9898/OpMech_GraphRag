"""
Enhanced Evidence Preprocessor

Enriches evidence with:
- Fiscal year/quarter labels
- Pre-computed period-over-period changes
- Multi-period trend analysis
- Metric type detection

This prevents LLM temporal interpretation errors by providing
explicit, pre-computed change information.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, date
from dataclasses import dataclass
import re
from loguru import logger

from .company_config import (
    FiscalConfig,
    get_company_config,
    detect_company_from_content,
    get_fiscal_period_label,
    DEFAULT_CONFIG,
)
from .metric_types import (
    MetricConfig,
    MetricType,
    ChangeDirection,
    ChangeResult,
    get_metric_config,
    compute_change,
    format_value,
)

# BUG 1 FIX: Forbidden generic labels that should NEVER appear in output
FORBIDDEN_GENERIC_LABELS = {'FY1', 'FY2', 'FY3', 'FY4', 'FY5', 'Period1', 'Period2'}


@dataclass
class TrendAnalysis:
    """Analysis of multi-period trend."""
    pattern: str  # 'accelerating_growth', 'decelerating_decline', 'reversal', etc.
    description: str
    periods: List[str]
    values: List[float]
    changes: List[ChangeResult]


class EvidencePreprocessor:
    """
    Preprocesses evidence to add temporal context and computed metrics.

    Key features:
    - Adds explicit fiscal year/quarter labels
    - Pre-computes period-over-period changes
    - Handles different metric types (%, $, ratios)
    - Detects multi-period trends
    - Company-specific fiscal year handling
    """

    def __init__(self, company_ticker: Optional[str] = None):
        """
        Initialize preprocessor.

        Args:
            company_ticker: Stock ticker for company-specific fiscal config.
                           If None, will try to auto-detect from content.
        """
        self.company_ticker = company_ticker
        self.fiscal_config = get_company_config(company_ticker) if company_ticker else None

        # Date parsing patterns
        self.date_patterns = [
            (r'(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'),                    # 2023-09-30
            (r'(\d{2}/\d{2}/\d{4})', '%m/%d/%Y'),                    # 09/30/2023
            (r'(\w+ \d{1,2}, \d{4})', '%B %d, %Y'),                  # September 30, 2023
            (r'(\w+ \d{4})', '%B %Y'),                               # September 2023
            (r'FY(\d{4})', None),                                     # FY2023 (fiscal year only)
            (r'Q([1-4])[-\s]?(?:FY)?(\d{4})', None),                 # Q3-2023 or Q3-FY2023
        ]

    def preprocess(self, evidence_nodes: List[Dict]) -> List[Dict]:
        """
        Enrich evidence nodes with temporal context and computed metrics.

        Args:
            evidence_nodes: List of evidence node dictionaries

        Returns:
            Enriched evidence nodes with fiscal labels and computed changes
        """
        if not evidence_nodes:
            return evidence_nodes

        # Auto-detect company if not provided
        if not self.fiscal_config:
            self.fiscal_config = self._detect_company_config(evidence_nodes)

        enriched = []

        # First pass: Add fiscal period labels
        for node in evidence_nodes:
            enriched_node = self._enrich_node(node)
            enriched.append(enriched_node)

        # Sort by fiscal period
        enriched = self._sort_chronologically(enriched)

        # Second pass: Compute period-over-period changes
        enriched = self._compute_sequential_changes(enriched)

        # Third pass: Compute multi-period trends (for 3+ periods)
        enriched = self._compute_trends(enriched)

        return enriched

    def _detect_company_config(self, nodes: List[Dict]) -> FiscalConfig:
        """Try to detect company from evidence content."""
        for node in nodes:
            content = node.get('content', '') or node.get('text', '')
            ticker = detect_company_from_content(content)
            if ticker:
                logger.debug(f"Auto-detected company: {ticker}")
                return get_company_config(ticker)

        logger.debug("Could not detect company, using default calendar year config")
        return DEFAULT_CONFIG

    def _enrich_node(self, node: Dict) -> Dict:
        """
        Add fiscal period and metric information to a single node.

        BUG 1 FIX: Always uses EXPLICIT fiscal year labels (FY2022, Q1-FY2024).
        NEVER uses generic labels (FY1, FY2, earlier period, later period).
        """
        enriched = node.copy()

        # Extract date from multiple possible locations
        date_str = node.get('period_end') or node.get('date') or node.get('period')
        if not date_str:
            # Check metadata
            metadata = node.get('metadata', {})
            if isinstance(metadata, dict):
                date_str = metadata.get('period_end') or metadata.get('period')

        if not date_str:
            date_str = self._extract_date_from_content(node.get('content', '') or node.get('text', ''))

        # Parse date and determine fiscal period
        if date_str:
            parsed = self._parse_date(date_str)
            if parsed:
                fiscal_year = self.fiscal_config.get_fiscal_year_for_date(parsed)
                fiscal_quarter = self.fiscal_config.get_quarter_for_month(parsed.month)

                # Determine if this is annual (year-end) or quarterly
                is_annual = self._is_annual_figure(node, parsed)

                enriched['fiscal_year'] = fiscal_year
                enriched['fiscal_quarter'] = fiscal_quarter

                # BUG 1 FIX: Generate EXPLICIT label with actual year
                # Format: "FY2023" for annual, "Q1-FY2024" for quarterly
                if is_annual:
                    enriched['fiscal_label'] = f"FY{fiscal_year}"
                else:
                    enriched['fiscal_label'] = f"Q{fiscal_quarter}-FY{fiscal_year}"

                enriched['parsed_date'] = parsed
                enriched['is_annual'] = is_annual

                # BUG 1 FIX: Validate label is not generic
                if enriched['fiscal_label'] in FORBIDDEN_GENERIC_LABELS:
                    logger.warning(f"Generated forbidden generic label {enriched['fiscal_label']}, fixing...")
                    enriched['fiscal_label'] = f"FY{fiscal_year}"  # Fallback to explicit
            else:
                # Try to parse FY label directly - must include actual year
                fy_match = re.search(r'FY(\d{4})', str(date_str))
                if fy_match:
                    year = int(fy_match.group(1))
                    enriched['fiscal_year'] = year
                    enriched['fiscal_label'] = f"FY{year}"  # Explicit year, not FY1/FY2
                    enriched['is_annual'] = True
                else:
                    # BUG 1 FIX: Try to extract year from date string
                    year_match = re.search(r'\b(20\d{2})\b', str(date_str))
                    if year_match:
                        year = int(year_match.group(1))
                        enriched['fiscal_year'] = year
                        enriched['fiscal_label'] = f"FY{year}"
                        enriched['is_annual'] = True
                    else:
                        # Cannot determine year - mark explicitly
                        enriched['fiscal_label'] = "Year-Unknown"
                        logger.debug(f"Could not extract year from: {date_str}")

        # Detect metric type
        xbrl_tag = node.get('xbrl_tag')
        if not xbrl_tag:
            metadata = node.get('metadata', {})
            if isinstance(metadata, dict):
                xbrl_tag = metadata.get('xbrl_tag')

        metric_config = get_metric_config(
            xbrl_tag=xbrl_tag,
            content=node.get('content', '') or node.get('text', '')
        )
        enriched['metric_config'] = metric_config
        enriched['metric_type'] = metric_config.metric_type.value

        # Format value if present
        value = self._extract_value(node)
        if value is not None:
            enriched['value'] = value
            enriched['formatted_value'] = format_value(value, metric_config)

        return enriched

    def _extract_date_from_content(self, content: str) -> Optional[str]:
        """Extract date string from content."""
        if not content:
            return None

        for pattern, _ in self.date_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(0)
        return None

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse a date string into a date object."""
        if not date_str:
            return None

        for pattern, fmt in self.date_patterns:
            match = re.search(pattern, str(date_str))
            if match:
                if fmt:
                    try:
                        return datetime.strptime(match.group(1), fmt).date()
                    except ValueError:
                        continue
                else:
                    # Handle FY or Q formats
                    if 'FY' in pattern:
                        year = int(match.group(1))
                        # Assume fiscal year end
                        return date(year, self.fiscal_config.fiscal_year_end_month, 28)
                    elif 'Q' in pattern:
                        quarter = int(match.group(1))
                        year = int(match.group(2))
                        # Estimate quarter end month
                        quarter_end_month = (self.fiscal_config.fiscal_year_end_month + quarter * 3 - 3) % 12 + 1
                        return date(year, quarter_end_month, 28)

        return None

    def _is_annual_figure(self, node: Dict, parsed_date: date) -> bool:
        """Determine if this is an annual figure."""
        content = (node.get('content', '') or node.get('text', '')).lower()

        # Check content for annual indicators
        annual_indicators = ['annual', 'fiscal year', 'full year', 'fy20', 'year ended']
        if any(ind in content for ind in annual_indicators):
            return True

        # Check if date is near fiscal year end
        if parsed_date.month == self.fiscal_config.fiscal_year_end_month:
            return True

        return False

    def _sort_chronologically(self, nodes: List[Dict]) -> List[Dict]:
        """Sort nodes by fiscal period, oldest first."""
        def sort_key(node):
            fy = node.get('fiscal_year', 9999)
            fq = node.get('fiscal_quarter', 5)
            return (fy, fq, (node.get('content', '') or node.get('text', ''))[:50])

        return sorted(nodes, key=sort_key)

    def _compute_sequential_changes(self, nodes: List[Dict]) -> List[Dict]:
        """Compute period-over-period changes for matching metrics."""

        # Group by metric (using XBRL tag or content similarity)
        by_metric = self._group_by_metric(nodes)

        for metric_key, metric_nodes in by_metric.items():
            if len(metric_nodes) < 2:
                continue

            # Sort by period
            sorted_nodes = sorted(
                [n for n in metric_nodes if n.get('fiscal_year')],
                key=lambda x: (x['fiscal_year'], x.get('fiscal_quarter', 0))
            )

            # Compute sequential changes
            for i in range(1, len(sorted_nodes)):
                prev = sorted_nodes[i - 1]
                curr = sorted_nodes[i]

                prev_val = prev.get('value')
                curr_val = curr.get('value')

                if prev_val is not None and curr_val is not None:
                    change = compute_change(
                        from_value=float(prev_val),
                        to_value=float(curr_val),
                        from_period=prev.get('fiscal_label', 'prior'),
                        to_period=curr.get('fiscal_label', 'current'),
                        config=curr.get('metric_config', get_metric_config()),
                    )
                    curr['computed_change'] = change

        return nodes

    def _compute_trends(self, nodes: List[Dict]) -> List[Dict]:
        """Compute multi-period trends for metrics with 3+ periods."""

        by_metric = self._group_by_metric(nodes)

        for metric_key, metric_nodes in by_metric.items():
            # Need at least 3 periods for trend analysis
            nodes_with_changes = [n for n in metric_nodes if n.get('computed_change')]

            if len(nodes_with_changes) < 2:
                continue

            # Get the changes
            changes = [n['computed_change'] for n in nodes_with_changes]

            # Analyze trend pattern
            trend = self._analyze_trend_pattern(changes)

            # Add to the most recent node
            nodes_with_changes[-1]['trend_analysis'] = trend

        return nodes

    def _group_by_metric(self, nodes: List[Dict]) -> Dict[str, List[Dict]]:
        """Group nodes by their metric (XBRL tag or content similarity)."""
        groups: Dict[str, List[Dict]] = {}

        for node in nodes:
            # Use XBRL tag if available
            key = node.get('xbrl_tag')
            if not key:
                metadata = node.get('metadata', {})
                if isinstance(metadata, dict):
                    key = metadata.get('xbrl_tag')

            if not key:
                # Fall back to extracting metric name from content
                key = self._extract_metric_name(node.get('content', '') or node.get('text', ''))

            if not key:
                key = 'unknown'

            if key not in groups:
                groups[key] = []
            groups[key].append(node)

        return groups

    def _extract_metric_name(self, content: str) -> Optional[str]:
        """Extract a metric name from content for grouping."""
        if not content:
            return None

        # Common patterns
        patterns = [
            r'(Total (?:Net )?(?:Sales|Revenue|Income|Profit))',
            r'(Gross (?:Profit|Margin))',
            r'(Operating (?:Income|Expenses|Margin))',
            r'(Net (?:Income|Sales|Revenue))',
            r'(iPhone|iPad|Mac|Services|Wearables)',  # Apple segments
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).lower().strip()

        return None

    def _analyze_trend_pattern(self, changes: List[ChangeResult]) -> TrendAnalysis:
        """Analyze the pattern of changes across periods."""

        if len(changes) < 2:
            return TrendAnalysis(
                pattern='insufficient_data',
                description='Insufficient data for trend analysis',
                periods=[c.to_period for c in changes],
                values=[c.to_value for c in changes],
                changes=changes,
            )

        # Get percentage changes (or absolute for ratios)
        pct_changes = []
        for c in changes:
            if c.percentage_change is not None:
                pct_changes.append(c.percentage_change)
            else:
                pct_changes.append(c.absolute_change)

        # Determine pattern
        all_positive = all(c > 0 for c in pct_changes)
        all_negative = all(c < 0 for c in pct_changes)

        if all_positive:
            if pct_changes[-1] > pct_changes[-2]:
                pattern = 'accelerating_growth'
                description = 'Growth is accelerating'
            else:
                pattern = 'decelerating_growth'
                description = 'Growth is slowing but still positive'
        elif all_negative:
            if pct_changes[-1] < pct_changes[-2]:
                pattern = 'accelerating_decline'
                description = 'Decline is accelerating'
            else:
                pattern = 'decelerating_decline'
                description = 'Decline is slowing'
        else:
            # Direction changed
            if pct_changes[-1] > 0 and pct_changes[-2] < 0:
                pattern = 'reversal_to_growth'
                description = 'Reversed from decline to growth'
            elif pct_changes[-1] < 0 and pct_changes[-2] > 0:
                pattern = 'reversal_to_decline'
                description = 'Reversed from growth to decline'
            else:
                pattern = 'volatile'
                description = 'Volatile with mixed direction changes'

        return TrendAnalysis(
            pattern=pattern,
            description=description,
            periods=[c.to_period for c in changes],
            values=[c.to_value for c in changes],
            changes=changes,
        )

    def _extract_value(self, node: Dict) -> Optional[float]:
        """Extract numerical value from node."""
        # Try direct value field
        value = node.get('value')
        if value is not None:
            try:
                return float(value)
            except (ValueError, TypeError):
                pass

        # Try metadata
        metadata = node.get('metadata', {})
        if isinstance(metadata, dict):
            value = metadata.get('value')
            if value is not None:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    pass

        # Try to extract from content
        content = node.get('content', '') or node.get('text', '')
        if content:
            # Match patterns like $394.33B, 394.33 billion, $383,290,000,000
            patterns = [
                (r'\$?([\d,.]+)\s*[Bb](?:illion)?', 1e9),  # $394.33B or 394.33 billion
                (r'\$?([\d,]+)\s*(?:million|M)', 1e6),     # $394 million or 394M
                (r'\$([\d,.]+)', 1),                        # $394.33
            ]

            for pattern, multiplier in patterns:
                match = re.search(pattern, content)
                if match:
                    num_str = match.group(1).replace(',', '')
                    try:
                        return float(num_str) * multiplier
                    except ValueError:
                        continue

        return None

    def format_for_llm(self, nodes: List[Dict], max_nodes: int = 8, max_content_len: int = 300) -> str:
        """
        Format preprocessed evidence for LLM consumption.

        Includes explicit temporal labels and pre-computed changes.
        Limited to stay within LLM context bounds.

        Args:
            nodes: List of evidence nodes
            max_nodes: Maximum number of nodes to include (default 8)
            max_content_len: Maximum content length per node (default 300)
        """
        lines = []

        # Limit nodes to prevent context overflow
        limited_nodes = nodes[:max_nodes]

        # Collect fiscal years from limited nodes
        fiscal_years_in_evidence = sorted(set(
            n.get('fiscal_label', '') for n in limited_nodes
            if n.get('fiscal_label') and n.get('fiscal_label') not in FORBIDDEN_GENERIC_LABELS
        ))

        # Concise header
        if fiscal_years_in_evidence:
            lines.append(f"PERIODS: {', '.join(fiscal_years_in_evidence)}. Use ONLY these labels.\n")

        for node in limited_nodes:
            # Build the evidence line
            node_type = node.get('type') or node.get('node_type', 'UNKNOWN')
            fiscal_label = node.get('fiscal_label', '')
            content = (node.get('content', '') or node.get('text', ''))[:max_content_len]

            # BUG 1 FIX: Validate fiscal label is explicit
            if fiscal_label and fiscal_label in FORBIDDEN_GENERIC_LABELS:
                logger.warning(f"Skipping forbidden generic label in LLM output: {fiscal_label}")
                fiscal_label = ''  # Don't include generic labels

            # Add fiscal year prefix if available and explicit
            if fiscal_label and fiscal_label not in FORBIDDEN_GENERIC_LABELS:
                line = f"[{node_type}] [{fiscal_label}] {content}"
            else:
                line = f"[{node_type}] {content}"

            # Add formatted value if different from content
            if 'formatted_value' in node and node['formatted_value'] not in content:
                line += f" (Value: {node['formatted_value']})"

            # Add computed change if available
            if 'computed_change' in node:
                change = node['computed_change']

                # BUG 1 FIX: Ensure change periods are explicit
                from_period = change.from_period if hasattr(change, 'from_period') else str(change.get('from_period', ''))
                to_period = change.to_period if hasattr(change, 'to_period') else str(change.get('to_period', ''))

                # Skip if periods are generic
                if from_period in FORBIDDEN_GENERIC_LABELS or to_period in FORBIDDEN_GENERIC_LABELS:
                    logger.warning(f"Skipping change with generic period labels: {from_period} -> {to_period}")
                    continue

                formatted_change = change.formatted_change if hasattr(change, 'formatted_change') else str(change)
                change_line = (
                    f"    -> Change from {from_period} to {to_period}: "
                    f"{formatted_change}"
                )

                # Add favorability indicator
                is_favorable = change.is_favorable if hasattr(change, 'is_favorable') else change.get('is_favorable')
                if is_favorable is not None:
                    indicator = "Favorable" if is_favorable else "Unfavorable"
                    change_line += f" [{indicator}]"

                line += "\n" + change_line

            # Add trend analysis if available
            if 'trend_analysis' in node:
                trend = node['trend_analysis']
                trend_line = f"    -> Trend: {trend.description} ({trend.pattern})"
                line += "\n" + trend_line

            lines.append(line)

        return "\n\n".join(lines)

    def get_temporal_summary(self, nodes: List[Dict]) -> str:
        """
        Generate a temporal summary of the evidence.

        Args:
            nodes: List of enriched evidence nodes

        Returns:
            Summary string describing temporal coverage and changes
        """
        # Collect fiscal years
        fiscal_years = sorted(set(n.get('fiscal_year') for n in nodes if n.get('fiscal_year')))

        # Collect changes
        changes = [n['computed_change'] for n in nodes if 'computed_change' in n]

        summary_parts = []

        if fiscal_years:
            summary_parts.append(f"Evidence covers: {', '.join(f'FY{fy}' for fy in fiscal_years)}")

        if changes:
            summary_parts.append("\nKey changes identified:")
            for change in changes:
                summary_parts.append(
                    f"  - {change.from_period} to {change.to_period}: "
                    f"{change.formatted_change}"
                )

        return "\n".join(summary_parts) if summary_parts else "No temporal context available"


# Factory function
def create_evidence_preprocessor(company: str = "apple") -> EvidencePreprocessor:
    """
    Create an evidence preprocessor for a specific company.

    Args:
        company: Company name or ticker (e.g., 'apple', 'AAPL', 'microsoft', 'MSFT')

    Returns:
        Configured EvidencePreprocessor instance
    """
    # Map company names to tickers
    name_to_ticker = {
        "apple": "AAPL",
        "microsoft": "MSFT",
        "google": "GOOGL",
        "alphabet": "GOOGL",
        "amazon": "AMZN",
        "meta": "META",
        "facebook": "META",
        "nvidia": "NVDA",
        "walmart": "WMT",
        "costco": "COST",
        "jpmorgan": "JPM",
        "bank of america": "BAC",
    }

    # Normalize company name to ticker
    ticker = name_to_ticker.get(company.lower(), company.upper())

    return EvidencePreprocessor(company_ticker=ticker)
