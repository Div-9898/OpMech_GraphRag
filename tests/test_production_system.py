"""
Comprehensive Test Suite for OpMech Production System

Tests the complete, production-grade solution including:
- Type-safe data models (FiscalPeriod, FinancialValue)
- Evidence extraction with proper type separation
- Temporal intelligence and direction validation
- Robust consistency checking
- Integration tests

KEY PRINCIPLE: These tests verify that the system CANNOT confuse
FY2023 with $2,023 because they are fundamentally different types.
"""

import unittest
from decimal import Decimal
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from opmech.type_safe_models import (
    FiscalPeriod,
    FinancialValue,
    Direction,
    Discrepancy,
    DiscrepancyType,
    Severity,
    ConsistencyReport,
    OperatorOutput,
    EvidenceNode,
    ComputedChange,
)
from opmech.evidence_extractor import (
    EvidenceExtractor,
    EvidenceSet,
    create_evidence_extractor,
)
from opmech.temporal_intelligence import (
    TemporalIntelligence,
    XBRLGroundTruth,
    create_temporal_intelligence,
)
from opmech.robust_consistency_checker import (
    RobustConsistencyChecker,
    check_operator_consistency,
    ConsistencyValidator,
)


class TestFiscalPeriod(unittest.TestCase):
    """Test FiscalPeriod class functionality."""

    def test_basic_creation(self):
        """Test basic FiscalPeriod creation."""
        period = FiscalPeriod(year=2023)
        self.assertEqual(period.year, 2023)
        self.assertIsNone(period.quarter)
        self.assertEqual(period.label, "FY2023")

    def test_quarterly_creation(self):
        """Test quarterly FiscalPeriod creation."""
        period = FiscalPeriod(year=2023, quarter=3)
        self.assertEqual(period.year, 2023)
        self.assertEqual(period.quarter, 3)
        self.assertEqual(period.label, "Q3-FY2023")

    def test_parse_fy_format(self):
        """Test parsing FY2023 format."""
        period = FiscalPeriod.from_string("FY2023")
        self.assertIsNotNone(period)
        self.assertEqual(period.year, 2023)
        self.assertIsNone(period.quarter)

    def test_parse_quarter_format(self):
        """Test parsing Q1-2024 format."""
        period = FiscalPeriod.from_string("Q1-2024")
        self.assertIsNotNone(period)
        self.assertEqual(period.year, 2024)
        self.assertEqual(period.quarter, 1)

    def test_parse_quarter_fy_format(self):
        """Test parsing Q1-FY2024 format."""
        period = FiscalPeriod.from_string("Q1-FY2024")
        self.assertIsNotNone(period)
        self.assertEqual(period.year, 2024)
        self.assertEqual(period.quarter, 1)

    def test_parse_short_year(self):
        """Test parsing FY23 short format."""
        period = FiscalPeriod.from_string("FY23")
        self.assertIsNotNone(period)
        self.assertEqual(period.year, 2023)

    def test_reject_dollar_amount(self):
        """Test that dollar amounts are rejected."""
        period = FiscalPeriod.from_string("$2023")
        self.assertIsNone(period)

        period = FiscalPeriod.from_string("2023 billion")
        self.assertIsNone(period)

    def test_immutability(self):
        """Test that FiscalPeriod is immutable."""
        period = FiscalPeriod(year=2023)
        with self.assertRaises(Exception):
            period.year = 2024

    def test_comparison(self):
        """Test FiscalPeriod comparison."""
        p1 = FiscalPeriod(year=2022)
        p2 = FiscalPeriod(year=2023)
        p3 = FiscalPeriod(year=2023, quarter=1)

        self.assertTrue(p1 < p2)
        self.assertTrue(p3 < p2)  # Q1 comes before annual
        self.assertTrue(p1 < p3)


class TestFinancialValue(unittest.TestCase):
    """Test FinancialValue class functionality."""

    def test_basic_creation(self):
        """Test basic FinancialValue creation."""
        value = FinancialValue(amount=Decimal("383.3"), scale="billions")
        self.assertEqual(value.amount, Decimal("383.3"))
        self.assertEqual(value.scale, "billions")

    def test_normalized_amount(self):
        """Test normalized amount calculation."""
        value = FinancialValue(amount=Decimal("383.3"), scale="billions")
        expected = Decimal("383.3") * Decimal("1000000000")
        self.assertEqual(value.normalized_amount, expected)

    def test_in_billions(self):
        """Test in_billions property."""
        value = FinancialValue(amount=Decimal("383300"), scale="millions")
        self.assertAlmostEqual(float(value.in_billions), 383.3, places=1)

    def test_format_billions(self):
        """Test formatting in billions."""
        value = FinancialValue(amount=Decimal("383.3"), scale="billions")
        formatted = value.format()
        self.assertTrue(formatted.startswith("$"))
        self.assertIn("B", formatted)
        self.assertIn("383", formatted)

    def test_parse_dollar_billion(self):
        """Test parsing $383.3B format."""
        value = FinancialValue.parse("$383.3B")
        self.assertIsNotNone(value)
        self.assertAlmostEqual(float(value.in_billions), 383.3, places=1)

    def test_parse_dollar_billion_word(self):
        """Test parsing $383.3 billion format."""
        value = FinancialValue.parse("$383.3 billion")
        self.assertIsNotNone(value)
        self.assertAlmostEqual(float(value.in_billions), 383.3, places=1)

    def test_parse_number_billion(self):
        """Test parsing 383.3B format (without $)."""
        value = FinancialValue.parse("383.3B")
        self.assertIsNotNone(value)
        self.assertAlmostEqual(float(value.in_billions), 383.3, places=1)

    def test_reject_bare_year(self):
        """Test that bare years are rejected."""
        value = FinancialValue.parse("2023")
        self.assertIsNone(value)

        value = FinancialValue.parse("FY2023")
        self.assertIsNone(value)

    def test_reject_fiscal_year_indicator(self):
        """Test that fiscal year indicators are rejected."""
        value = FinancialValue.parse("$FY2023")
        self.assertIsNone(value)

    def test_immutability(self):
        """Test that FinancialValue is immutable."""
        value = FinancialValue(amount=Decimal("100"))
        with self.assertRaises(Exception):
            value.amount = Decimal("200")

    def test_arithmetic(self):
        """Test FinancialValue arithmetic."""
        v1 = FinancialValue(amount=Decimal("100"), scale="billions")
        v2 = FinancialValue(amount=Decimal("90"), scale="billions")

        diff = v1 - v2
        self.assertEqual(diff.normalized_amount, Decimal("10") * Decimal("1000000000"))


class TestTypeSafety(unittest.TestCase):
    """Test that types are never confused - the core fix."""

    def test_year_not_parsed_as_money(self):
        """FY2023 should never become $2,023 - THE CRITICAL TEST."""
        text = "In FY2023, revenue was $383.3 billion"
        extractor = EvidenceExtractor()
        node = extractor.extract_from_text(text)

        # Periods should be FiscalPeriod objects
        self.assertEqual(len(node.periods), 1)
        self.assertIsInstance(node.periods[0], FiscalPeriod)
        self.assertEqual(node.periods[0].year, 2023)

        # Values should be FinancialValue objects
        self.assertEqual(len(node.values), 1)
        self.assertIsInstance(node.values[0], FinancialValue)
        self.assertAlmostEqual(float(node.values[0].in_billions), 383.3, places=1)

        # The year 2023 should NOT appear in values
        for value in node.values:
            self.assertNotEqual(float(value.amount), 2023)
            self.assertNotEqual(float(value.amount), 2.023)

    def test_multiple_years_not_parsed_as_money(self):
        """Multiple years in text should not become dollar amounts."""
        text = "Revenue decreased from FY2022 to FY2023, falling from $394.3B to $383.3B"
        extractor = EvidenceExtractor()
        node = extractor.extract_from_text(text)

        # Should have 2 periods
        self.assertEqual(len(node.periods), 2)
        years = {p.year for p in node.periods}
        self.assertEqual(years, {2022, 2023})

        # Should have 2 values
        self.assertEqual(len(node.values), 2)
        amounts = {float(v.in_billions) for v in node.values}

        # Neither 2022 nor 2023 should appear as dollar amounts
        for v in node.values:
            self.assertNotAlmostEqual(float(v.in_billions), 2.022, places=2)
            self.assertNotAlmostEqual(float(v.in_billions), 2.023, places=2)

    def test_consistency_checker_type_safety(self):
        """Consistency checker should never compare years to dollars."""
        checker = RobustConsistencyChecker()

        # Simulate two outputs that mention the same period differently
        output_a = OperatorOutput(
            operator_name="A",
            strategy="structure-first",
            raw_answer="Revenue was $383.3 billion in FY2023",
            confidence=0.8
        )
        output_b = OperatorOutput(
            operator_name="B",
            strategy="narrative-first",
            raw_answer="FY2023 revenue totaled $383.3B",
            confidence=0.8
        )

        report = checker.check_consistency(output_a, output_b)

        # Should have NO discrepancies (same data, different wording)
        # And definitely no "$2,023" appearing anywhere
        self.assertNotIn("$2,023", report.analyst_notes)
        self.assertNotIn("$2,024", report.analyst_notes)
        self.assertNotIn("$2,022", report.analyst_notes)

    def test_different_value_types_not_compared(self):
        """Different value types should never be compared."""
        checker = RobustConsistencyChecker()

        # Output A mentions a year, output B mentions a dollar amount
        output_a = OperatorOutput(
            operator_name="A",
            strategy="structure-first",
            raw_answer="The fiscal year 2023 showed strong performance",
            confidence=0.8
        )
        output_b = OperatorOutput(
            operator_name="B",
            strategy="narrative-first",
            raw_answer="Revenue was $2,023 million",  # Different metric entirely
            confidence=0.8
        )

        report = checker.check_consistency(output_a, output_b)

        # Should NOT have a discrepancy comparing 2023 to $2,023
        for d in report.discrepancies:
            # If there's a numerical discrepancy, both values must be FinancialValue
            if d.discrepancy_type == DiscrepancyType.NUMERICAL:
                self.assertIsInstance(d.operator_a_value, FinancialValue)
                self.assertIsInstance(d.operator_b_value, FinancialValue)


class TestTemporalDirectionValidation(unittest.TestCase):
    """Test direction validation is always correct."""

    def setUp(self):
        self.temporal = TemporalIntelligence()

    def test_increase_detection(self):
        """Test increase direction detection."""
        is_valid, actual, explanation = self.temporal.validate_direction_claim(
            claimed_direction=Direction.INCREASE,
            from_period=FiscalPeriod(year=2022),
            to_period=FiscalPeriod(year=2023),
            from_value=FinancialValue(amount=Decimal("100"), scale="billions"),
            to_value=FinancialValue(amount=Decimal("110"), scale="billions")
        )
        self.assertTrue(is_valid)
        self.assertEqual(actual, Direction.INCREASE)
        self.assertIn("CORRECT", explanation)

    def test_decrease_detection(self):
        """Test decrease direction detection."""
        is_valid, actual, explanation = self.temporal.validate_direction_claim(
            claimed_direction=Direction.DECREASE,
            from_period=FiscalPeriod(year=2022),
            to_period=FiscalPeriod(year=2023),
            from_value=FinancialValue(amount=Decimal("394.33"), scale="billions"),
            to_value=FinancialValue(amount=Decimal("383.29"), scale="billions")
        )
        self.assertTrue(is_valid)
        self.assertEqual(actual, Direction.DECREASE)
        self.assertIn("CORRECT", explanation)

    def test_wrong_claim_detection(self):
        """Test wrong claim detection."""
        is_valid, actual, explanation = self.temporal.validate_direction_claim(
            claimed_direction=Direction.INCREASE,  # WRONG claim
            from_period=FiscalPeriod(year=2022),
            to_period=FiscalPeriod(year=2023),
            from_value=FinancialValue(amount=Decimal("394.33"), scale="billions"),
            to_value=FinancialValue(amount=Decimal("383.29"), scale="billions")
        )
        self.assertFalse(is_valid)
        self.assertEqual(actual, Direction.DECREASE)
        self.assertIn("INCORRECT", explanation)

    def test_unchanged_detection(self):
        """Test unchanged direction detection."""
        is_valid, actual, explanation = self.temporal.validate_direction_claim(
            claimed_direction=Direction.UNCHANGED,
            from_period=FiscalPeriod(year=2022),
            to_period=FiscalPeriod(year=2023),
            from_value=FinancialValue(amount=Decimal("100"), scale="billions"),
            to_value=FinancialValue(amount=Decimal("100"), scale="billions")
        )
        self.assertTrue(is_valid)
        self.assertEqual(actual, Direction.UNCHANGED)

    def test_compute_change_description(self):
        """Test change description generation."""
        desc = self.temporal.compute_change_description(
            metric="Revenue",
            from_period=FiscalPeriod(year=2022),
            to_period=FiscalPeriod(year=2023),
            from_value=FinancialValue(amount=Decimal("394.33"), scale="billions"),
            to_value=FinancialValue(amount=Decimal("383.29"), scale="billions")
        )

        self.assertIn("Revenue", desc)
        self.assertIn("DECREASED", desc)
        self.assertIn("FY2022", desc)
        self.assertIn("FY2023", desc)
        self.assertIn("unfavorable", desc.lower())


class TestAnalystNotes(unittest.TestCase):
    """Test that analyst notes are clean and useful."""

    def test_no_duplicate_notes(self):
        """Analyst notes should never have duplicates."""
        checker = RobustConsistencyChecker()

        # Create outputs with potential for many discrepancies
        output_a = OperatorOutput(
            operator_name="A",
            strategy="structure-first",
            raw_answer="Revenue increased from $383B to $390B. Profit grew.",
            confidence=0.8
        )
        output_b = OperatorOutput(
            operator_name="B",
            strategy="narrative-first",
            raw_answer="Revenue decreased from $383B to $380B. Profit declined.",
            confidence=0.8
        )

        report = checker.check_consistency(output_a, output_b)

        # Count occurrences of each line
        lines = report.analyst_notes.split('\n')

        # Should have no exact duplicate lines (except empty lines)
        non_empty_lines = [l for l in lines if l.strip()]
        non_empty_unique = list(set(non_empty_lines))

        # The number of unique lines should equal total non-empty lines
        self.assertEqual(len(non_empty_lines), len(non_empty_unique))

    def test_notes_under_limit(self):
        """Analyst notes should be limited in length."""
        # Create many discrepancies manually
        discrepancies = [
            Discrepancy(
                discrepancy_type=DiscrepancyType.NUMERICAL,
                severity=Severity.MINOR,
                metric=f"metric_{i}",
                operator_a_value=FinancialValue(amount=Decimal(str(i)), scale="billions"),
                operator_b_value=FinancialValue(amount=Decimal(str(i + 1)), scale="billions")
            )
            for i in range(100)  # 100 potential discrepancies
        ]

        checker = RobustConsistencyChecker()
        notes = checker._generate_analyst_notes(discrepancies)

        # Should be limited
        lines = [l for l in notes.split('\n') if l.strip()]
        self.assertLess(len(lines), 20)

    def test_notes_no_garbage(self):
        """Analyst notes should not contain garbage like $2,023."""
        checker = RobustConsistencyChecker()

        output_a = OperatorOutput(
            operator_name="A",
            strategy="structure-first",
            raw_answer="In FY2023, revenue was $383.3 billion, up from FY2022's $394.3 billion",
            confidence=0.8
        )
        output_b = OperatorOutput(
            operator_name="B",
            strategy="narrative-first",
            raw_answer="FY2023 showed revenue of $383B compared to $394B in FY2022",
            confidence=0.8
        )

        report = checker.check_consistency(output_a, output_b)

        # Check for garbage values
        garbage_values = ["$2,023", "$2,022", "$2023", "$2022", "$20"]
        for garbage in garbage_values:
            self.assertNotIn(garbage, report.analyst_notes)


class TestEvidenceExtractor(unittest.TestCase):
    """Test evidence extraction functionality."""

    def setUp(self):
        self.extractor = EvidenceExtractor()

    def test_extract_single_value(self):
        """Test extracting a single financial value."""
        text = "Apple reported revenue of $383.3 billion"
        node = self.extractor.extract_from_text(text)

        self.assertEqual(len(node.values), 1)
        self.assertAlmostEqual(float(node.values[0].in_billions), 383.3, places=1)

    def test_extract_multiple_values(self):
        """Test extracting multiple financial values."""
        text = "Revenue was $383.3B and net income was $97.0B"
        node = self.extractor.extract_from_text(text)

        self.assertEqual(len(node.values), 2)
        amounts = {round(float(v.in_billions), 1) for v in node.values}
        self.assertEqual(amounts, {383.3, 97.0})

    def test_extract_period_and_value(self):
        """Test extracting both period and value."""
        text = "In FY2023, revenue was $383.3 billion"
        node = self.extractor.extract_from_text(text)

        self.assertEqual(len(node.periods), 1)
        self.assertEqual(node.periods[0].year, 2023)

        self.assertEqual(len(node.values), 1)
        # Value should be associated with the period
        self.assertEqual(node.values[0].period, node.periods[0])

    def test_extract_direction_claims(self):
        """Test extracting direction claims."""
        text = "Revenue increased significantly while costs decreased"
        claims = self.extractor.extract_direction_claims(text)

        # Should find both claims
        self.assertGreater(len(claims), 0)

        directions = {c['direction'] for c in claims}
        self.assertIn(Direction.INCREASE, directions)
        self.assertIn(Direction.DECREASE, directions)


class TestXBRLGroundTruth(unittest.TestCase):
    """Test XBRL ground truth validation."""

    def setUp(self):
        self.xbrl = XBRLGroundTruth()
        # Add some test data
        self.xbrl.add_value(
            company="AAPL",
            metric="Revenue",
            period=FiscalPeriod(year=2023),
            value=FinancialValue(amount=Decimal("383.29"), scale="billions")
        )
        self.xbrl.add_value(
            company="AAPL",
            metric="Revenue",
            period=FiscalPeriod(year=2022),
            value=FinancialValue(amount=Decimal("394.33"), scale="billions")
        )

    def test_get_value(self):
        """Test retrieving ground truth value."""
        value = self.xbrl.get_value("AAPL", "Revenue", FiscalPeriod(year=2023))
        self.assertIsNotNone(value)
        self.assertAlmostEqual(float(value.in_billions), 383.29, places=2)

    def test_validate_correct_claim(self):
        """Test validating a correct claim."""
        is_valid, ground_truth, explanation = self.xbrl.validate_claim(
            company="AAPL",
            metric="Revenue",
            period=FiscalPeriod(year=2023),
            claimed_value=FinancialValue(amount=Decimal("383.3"), scale="billions"),
            tolerance=0.05
        )
        self.assertTrue(is_valid)
        self.assertIn("VALID", explanation)

    def test_validate_incorrect_claim(self):
        """Test validating an incorrect claim."""
        # Use a value that differs by more than 5% from the ground truth of $383.29B
        # $450B is about 17% higher than $383.29B
        is_valid, ground_truth, explanation = self.xbrl.validate_claim(
            company="AAPL",
            metric="Revenue",
            period=FiscalPeriod(year=2023),
            claimed_value=FinancialValue(amount=Decimal("450"), scale="billions"),
            tolerance=0.05
        )
        self.assertFalse(is_valid)
        self.assertIn("INVALID", explanation)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""

    def test_full_pipeline(self):
        """Test the full evidence processing pipeline."""
        # Create extractor
        extractor = EvidenceExtractor(company="AAPL")

        # Extract from text
        text = """
        Apple's fiscal year 2023 results showed total net sales of $383.3 billion,
        a decrease from $394.3 billion in FY2022. This represents a decline of
        approximately 2.8% year-over-year.
        """
        node = extractor.extract_from_text(text, source="10-K")

        # Verify extraction
        self.assertGreaterEqual(len(node.periods), 2)
        self.assertGreaterEqual(len(node.values), 2)

        # Create temporal intelligence
        temporal = TemporalIntelligence(company="AAPL")

        # Compute changes
        if len(node.values) >= 2 and len(node.periods) >= 2:
            change = temporal.compute_change(
                metric_name="Revenue",
                from_period=FiscalPeriod(year=2022),
                to_period=FiscalPeriod(year=2023),
                from_value=FinancialValue(amount=Decimal("394.3"), scale="billions"),
                to_value=FinancialValue(amount=Decimal("383.3"), scale="billions")
            )

            self.assertEqual(change.direction, Direction.DECREASE)
            self.assertIsNotNone(change.percentage_change)
            self.assertLess(change.percentage_change, 0)

    def test_consistency_with_direction_disagreement(self):
        """Test consistency check catches direction disagreement."""
        checker = RobustConsistencyChecker(company="AAPL")

        output_a = OperatorOutput(
            operator_name="A",
            strategy="structure-first",
            raw_answer="Apple's revenue increased in FY2023 to $390B",
            confidence=0.8
        )
        output_b = OperatorOutput(
            operator_name="B",
            strategy="narrative-first",
            raw_answer="Apple's revenue decreased in FY2023 to $383B",
            confidence=0.8
        )

        report = checker.check_consistency(output_a, output_b)

        # Should detect direction discrepancy
        self.assertFalse(report.is_consistent)
        direction_discrepancies = [
            d for d in report.discrepancies
            if d.discrepancy_type == DiscrepancyType.DIRECTION
        ]
        self.assertGreater(len(direction_discrepancies), 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_empty_text(self):
        """Test handling empty text."""
        extractor = EvidenceExtractor()
        node = extractor.extract_from_text("")
        self.assertEqual(len(node.periods), 0)
        self.assertEqual(len(node.values), 0)

    def test_no_financial_data(self):
        """Test handling text with no financial data."""
        extractor = EvidenceExtractor()
        text = "This is just regular text without any numbers or dates."
        node = extractor.extract_from_text(text)
        self.assertEqual(len(node.periods), 0)
        self.assertEqual(len(node.values), 0)

    def test_malformed_values(self):
        """Test handling malformed values."""
        value = FinancialValue.parse("$abc million")
        self.assertIsNone(value)

        value = FinancialValue.parse("not a number")
        self.assertIsNone(value)

    def test_invalid_fiscal_period(self):
        """Test handling invalid fiscal periods."""
        # Invalid year
        with self.assertRaises(ValueError):
            FiscalPeriod(year=1800)

        # Invalid quarter
        with self.assertRaises(ValueError):
            FiscalPeriod(year=2023, quarter=5)

    def test_consistency_with_empty_answers(self):
        """Test consistency check with empty answers."""
        checker = RobustConsistencyChecker()

        output_a = OperatorOutput(
            operator_name="A",
            strategy="structure-first",
            raw_answer="",
            confidence=0.0
        )
        output_b = OperatorOutput(
            operator_name="B",
            strategy="narrative-first",
            raw_answer="Some answer here",
            confidence=0.8
        )

        report = checker.check_consistency(output_a, output_b)

        # Should not crash, should be consistent (no comparable facts)
        self.assertTrue(report.is_consistent)


if __name__ == '__main__':
    unittest.main(verbosity=2)
