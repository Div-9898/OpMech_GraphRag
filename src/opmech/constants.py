"""Constants for OpMech-GraphRAG system.

Contains XBRL concept mappings for financial metrics retrieval.

FIX 8: Added comprehensive FINANCIAL_CONCEPT_MAP for semantic expansion.
"""

# XBRL concepts related to margins
MARGIN_XBRL_CONCEPTS = [
    # Gross Margin / Gross Profit
    "GrossProfit",
    "CostOfGoodsSold",
    "CostOfRevenue",
    "CostOfGoodsAndServicesSold",

    # Operating Margin
    "OperatingIncome",
    "OperatingExpenses",
    "OperatingIncomeLoss",

    # Net Margin
    "NetIncome",
    "NetIncomeLoss",
    "ProfitLoss",

    # Revenue (for calculating margins)
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",

    # Segment margins (Apple specific)
    "RevenueFromContractWithCustomerByProduct",
    "GrossMarginPercentage",
]

# =============================================================================
# FIX 8: Comprehensive Financial Concept Mapping
# =============================================================================

# Maps common financial terms to XBRL concepts
# This allows queries like "profitability" to find NetIncome, GrossProfit, etc.
FINANCIAL_CONCEPT_MAP = {
    # Profitability metrics
    "profitability": ["NetIncome", "GrossProfit", "OperatingIncome", "NetEarnings", "ProfitLoss"],
    "profit": ["NetIncome", "GrossProfit", "OperatingIncome", "ProfitLoss"],
    "earnings": ["NetIncome", "EarningsPerShare", "NetEarnings", "BasicEarningsPerShare", "DilutedEarningsPerShare"],
    "income": ["NetIncome", "OperatingIncome", "IncomeBeforeTax", "NetIncomeLoss"],

    # Revenue metrics
    "revenue": ["Revenues", "NetSales", "TotalRevenue", "SalesRevenueNet", "RevenueFromContractWithCustomerExcludingAssessedTax"],
    "sales": ["NetSales", "Revenues", "SalesRevenueNet", "TotalRevenue"],
    "growth": ["Revenues", "NetSales", "NetIncome", "GrossProfit"],
    "top line": ["Revenues", "NetSales", "TotalRevenue"],

    # Margin metrics
    "margin": ["GrossProfit", "OperatingIncome", "NetIncome", "GrossMarginPercentage"],
    "gross margin": ["GrossProfit", "CostOfGoodsSold", "CostOfRevenue", "GrossMarginPercentage"],
    "operating margin": ["OperatingIncome", "OperatingExpenses", "OperatingIncomeLoss"],
    "net margin": ["NetIncome", "NetIncomeLoss", "ProfitLoss"],
    "profit margin": ["GrossProfit", "OperatingIncome", "NetIncome"],

    # Cost metrics
    "costs": ["CostOfRevenue", "CostOfGoodsSold", "OperatingExpenses", "TotalCostsAndExpenses"],
    "expenses": ["OperatingExpenses", "ResearchAndDevelopmentExpense", "SellingGeneralAndAdministrativeExpense"],
    "r&d": ["ResearchAndDevelopmentExpense"],
    "research and development": ["ResearchAndDevelopmentExpense"],
    "sg&a": ["SellingGeneralAndAdministrativeExpense"],
    "cost of goods": ["CostOfGoodsSold", "CostOfRevenue"],
    "cogs": ["CostOfGoodsSold", "CostOfRevenue"],

    # Balance sheet - Assets
    "cash": ["CashAndCashEquivalents", "Cash", "CashCashEquivalentsAndShortTermInvestments"],
    "assets": ["TotalAssets", "Assets", "CurrentAssets"],
    "inventory": ["InventoryNet", "Inventory"],
    "receivables": ["AccountsReceivableNet", "AccountsReceivable"],
    "investments": ["ShortTermInvestments", "LongTermInvestments", "MarketableSecurities"],

    # Balance sheet - Liabilities
    "debt": ["LongTermDebt", "TotalDebt", "DebtCurrent", "LongTermDebtNoncurrent"],
    "liabilities": ["TotalLiabilities", "Liabilities", "CurrentLiabilities"],
    "payables": ["AccountsPayable", "AccountsPayableCurrent"],

    # Balance sheet - Equity
    "equity": ["StockholdersEquity", "TotalEquity", "ShareholdersEquity"],
    "retained earnings": ["RetainedEarnings", "RetainedEarningsAccumulatedDeficit"],
    "book value": ["StockholdersEquity", "BookValuePerShare"],

    # Cash flow metrics
    "cash flow": ["NetCashProvidedByOperatingActivities", "FreeCashFlow", "CashFlowFromOperations"],
    "operating cash flow": ["NetCashProvidedByOperatingActivities", "CashFlowFromOperations"],
    "free cash flow": ["FreeCashFlow", "NetCashProvidedByOperatingActivities"],
    "capex": ["CapitalExpenditures", "PaymentsToAcquirePropertyPlantAndEquipment"],
    "capital expenditure": ["CapitalExpenditures", "PaymentsToAcquirePropertyPlantAndEquipment"],

    # Per share metrics
    "eps": ["EarningsPerShare", "BasicEarningsPerShare", "DilutedEarningsPerShare"],
    "dividend": ["DividendsPerShare", "DividendsDeclared", "CommonStockDividendsPerShare"],
    "shares": ["CommonSharesOutstanding", "WeightedAverageSharesOutstanding"],

    # Performance metrics
    "performance": ["Revenues", "NetIncome", "OperatingIncome", "GrossProfit"],
    "financial health": ["TotalAssets", "TotalLiabilities", "CashAndCashEquivalents", "NetIncome", "StockholdersEquity"],
    "liquidity": ["CashAndCashEquivalents", "CurrentAssets", "CurrentLiabilities", "QuickRatio"],
    "leverage": ["TotalDebt", "TotalLiabilities", "StockholdersEquity", "DebtToEquityRatio"],
    "solvency": ["TotalAssets", "TotalLiabilities", "StockholdersEquity"],

    # Return metrics
    "roe": ["NetIncome", "StockholdersEquity", "ReturnOnEquity"],
    "roa": ["NetIncome", "TotalAssets", "ReturnOnAssets"],
    "roi": ["NetIncome", "TotalAssets", "ReturnOnInvestment"],
    "roic": ["OperatingIncome", "InvestedCapital", "ReturnOnInvestedCapital"],
}


def expand_query_to_xbrl(query: str) -> list:
    """
    FIX 8: Expand query terms to relevant XBRL concepts.

    This allows queries like "How has Apple's profitability trended?" to find
    NetIncome, GrossProfit, etc. instead of failing with "no data".

    Args:
        query: User query string

    Returns:
        List of XBRL concept names to search for
    """
    expanded_tags = []
    query_lower = query.lower()

    for concept, tags in FINANCIAL_CONCEPT_MAP.items():
        if concept in query_lower:
            expanded_tags.extend(tags)

    # Remove duplicates while preserving order
    seen = set()
    unique_tags = []
    for tag in expanded_tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)

    return unique_tags


# Query term to XBRL concept mapping (legacy, kept for compatibility)
# Maps natural language query terms to relevant XBRL concepts
QUERY_TO_XBRL_MAP = {
    "gross margin": ["GrossProfit", "CostOfGoodsSold", "CostOfRevenue", "GrossMarginPercentage"],
    "gross profit": ["GrossProfit", "CostOfGoodsSold", "CostOfRevenue"],
    "operating margin": ["OperatingIncome", "OperatingExpenses", "OperatingIncomeLoss"],
    "net margin": ["NetIncome", "NetIncomeLoss", "ProfitLoss"],
    "profit margin": ["GrossProfit", "OperatingIncome", "NetIncome", "ProfitLoss"],
    "margin": ["GrossProfit", "OperatingIncome", "NetIncome", "CostOfGoodsSold", "CostOfRevenue"],
    "revenue": ["Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerExcludingAssessedTax"],
    "cost": ["CostOfGoodsSold", "CostOfRevenue", "OperatingExpenses"],
    "cost of sales": ["CostOfGoodsSold", "CostOfRevenue", "CostOfGoodsAndServicesSold"],
    "earnings": ["NetIncome", "NetIncomeLoss", "ProfitLoss", "EarningsPerShare"],
    "profit": ["GrossProfit", "NetIncome", "OperatingIncome", "ProfitLoss"],
    "income": ["NetIncome", "OperatingIncome", "NetIncomeLoss", "OperatingIncomeLoss"],
    # FIX 8: Add profitability mapping
    "profitability": ["NetIncome", "GrossProfit", "OperatingIncome", "NetEarnings", "ProfitLoss"],
}

# Terms that indicate a query has numerical/financial aspects
# even if classified as OPINION or other types
NUMERICAL_ASPECT_TERMS = [
    "margin", "revenue", "profit", "income", "expense", "cost",
    "growth", "decline", "increase", "decrease", "percentage", "%",
    "ratio", "eps", "earnings", "sales", "gross", "net", "operating"
]

# Financial term mappings for text-to-XBRL search
# Maps common terms to XBRL-friendly search terms
FINANCIAL_TERM_MAPPINGS = {
    "gross margin": ["gross margin", "gross profit", "cost of sales", "GrossProfit", "GrossMargin"],
    "margin": ["margin", "profit margin", "gross profit"],
    "revenue": ["revenue", "net sales", "total revenue", "Revenues"],
    "profit": ["profit", "net income", "operating income", "NetIncome"],
    "cost": ["cost", "expenses", "cost of sales", "operating expenses"],
    "earnings": ["earnings", "eps", "net income", "EarningsPerShare"],
}
