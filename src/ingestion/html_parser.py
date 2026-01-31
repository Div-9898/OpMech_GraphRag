"""HTML parser for extracting content from SEC filings."""

import re
from pathlib import Path
from typing import Generator

import pandas as pd
from bs4 import BeautifulSoup, NavigableString, Tag
from loguru import logger

from src.config import settings
from src.models import Node, NodeMetadata, NodeType


class HTMLParser:
    """Parses SEC filing HTML documents to extract structured content."""

    # SEC filing section patterns
    SECTION_PATTERNS = {
        "Item 1": r"Item\s*1[.\s]+Business",
        "Item 1A": r"Item\s*1A[.\s]+Risk\s*Factors",
        "Item 1B": r"Item\s*1B[.\s]+Unresolved\s*Staff\s*Comments",
        "Item 2": r"Item\s*2[.\s]+Properties",
        "Item 3": r"Item\s*3[.\s]+Legal\s*Proceedings",
        "Item 4": r"Item\s*4[.\s]+Mine\s*Safety",
        "Item 5": r"Item\s*5[.\s]+Market",
        "Item 6": r"Item\s*6[.\s]+\[?Reserved\]?",
        "Item 7": r"Item\s*7[.\s]+Management['\u2019]?s?\s*Discussion",
        "Item 7A": r"Item\s*7A[.\s]+Quantitative",
        "Item 8": r"Item\s*8[.\s]+Financial\s*Statements",
        "Item 9": r"Item\s*9[.\s]+Changes\s*in",
        "Item 9A": r"Item\s*9A[.\s]+Controls",
        "Item 9B": r"Item\s*9B[.\s]+Other\s*Information",
        "Item 10": r"Item\s*10[.\s]+Directors",
        "Item 11": r"Item\s*11[.\s]+Executive\s*Compensation",
        "Item 12": r"Item\s*12[.\s]+Security\s*Ownership",
        "Item 13": r"Item\s*13[.\s]+Certain\s*Relationships",
        "Item 14": r"Item\s*14[.\s]+Principal",
        "Item 15": r"Item\s*15[.\s]+Exhibits",
    }

    NOTE_PATTERN = r"Note\s*(\d+)[.\s]*[-–—]?\s*(.+?)(?=\n|$)"

    def __init__(self, filing_id: str, period: str):
        self.filing_id = filing_id
        self.period = period
        self.node_counters = {t: 0 for t in NodeType}

    def _generate_node_id(self, node_type: NodeType) -> str:
        """Generate a unique node ID."""
        self.node_counters[node_type] += 1
        type_abbrev = {
            NodeType.FINANCIAL_LINE: "FL",
            NodeType.TEXT_SECTION: "TS",
            NodeType.NOTE: "NT",
            NodeType.TABLE_ROW: "TR",
            NodeType.ENTITY: "EN",
        }
        return f"{self.filing_id}_{type_abbrev[node_type]}_{self.node_counters[node_type]:04d}"

    def parse_file(self, file_path: Path) -> list[Node]:
        """Parse an SEC filing HTML file."""
        logger.info(f"Parsing {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html5lib")

        nodes = []

        # Extract sections
        nodes.extend(self._extract_sections(soup))

        # Extract tables
        nodes.extend(self._extract_tables(soup))

        # Extract notes
        nodes.extend(self._extract_notes(soup))

        logger.info(f"Extracted {len(nodes)} nodes from {file_path.name}")
        return nodes

    def _extract_sections(self, soup: BeautifulSoup) -> list[Node]:
        """Extract text sections from the filing."""
        nodes = []

        # Get all text content
        text = soup.get_text(separator="\n", strip=True)

        # Find section boundaries
        section_positions = []
        for section_name, pattern in self.SECTION_PATTERNS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                section_positions.append((match.start(), section_name, match.group()))

        # Sort by position
        section_positions.sort(key=lambda x: x[0])

        # Extract content between sections
        for i, (start_pos, section_name, header) in enumerate(section_positions):
            # Find end position (start of next section or end of text)
            if i + 1 < len(section_positions):
                end_pos = section_positions[i + 1][0]
            else:
                end_pos = len(text)

            section_text = text[start_pos:end_pos].strip()

            # Skip very short sections
            if len(section_text) < 100:
                continue

            # Split into paragraphs
            paragraphs = self._split_into_paragraphs(section_text)

            # Determine chunk size based on section importance
            # MD&A (Item 7) and Risk Factors (Item 1A) get larger chunks
            if section_name in ["Item 7", "Item 7A"]:
                max_chunk_size = settings.chunk_size_mda
            elif section_name == "Item 1A":
                max_chunk_size = settings.chunk_size_risk
            else:
                max_chunk_size = settings.chunk_size_default

            for para_idx, para in enumerate(paragraphs):
                if len(para.strip()) < settings.chunk_min_length:
                    continue

                # Truncate to max chunk size (configurable)
                para_text = para[:max_chunk_size]

                node = Node(
                    id=self._generate_node_id(NodeType.TEXT_SECTION),
                    type=NodeType.TEXT_SECTION,
                    text=para_text,
                    metadata=NodeMetadata(
                        filing_id=self.filing_id,
                        period=self.period,
                        section=section_name,
                        char_offset=start_pos,
                    ),
                )
                nodes.append(node)

        return nodes

    def _split_into_paragraphs(self, text: str, min_length: int = 100, max_length: int = None) -> list[str]:
        """
        Split text into meaningful paragraphs, keeping related content together.

        Args:
            text: The text to split
            min_length: Minimum paragraph length (merge shorter ones)
            max_length: Maximum paragraph length (split longer ones)
        """
        if max_length is None:
            max_length = settings.chunk_size_default

        # Split on double newlines or multiple spaces
        raw_paragraphs = re.split(r"\n\s*\n|\n{2,}", text)

        paragraphs = []
        current = ""

        for para in raw_paragraphs:
            para = para.strip()
            if not para:
                continue

            # Clean up whitespace within paragraph
            para = re.sub(r"\s+", " ", para)

            # If adding this paragraph would exceed max_length, save current first
            if current and len(current) + len(para) + 1 > max_length:
                if len(current) >= min_length:
                    paragraphs.append(current)
                current = para
            # If paragraph is too short, merge with previous
            elif len(para) < min_length and current:
                current += " " + para
            else:
                if current and len(current) >= min_length:
                    paragraphs.append(current)
                current = para

        if current and len(current) >= min_length:
            paragraphs.append(current)

        return paragraphs

    def _extract_tables(self, soup: BeautifulSoup) -> list[Node]:
        """Extract table rows from the filing."""
        nodes = []

        tables = soup.find_all("table")
        logger.debug(f"Found {len(tables)} tables")

        for table_idx, table in enumerate(tables):
            table_id = f"{self.filing_id}_table_{table_idx}"

            try:
                # Try to parse with pandas
                df = pd.read_html(str(table))[0]

                # Clean up the dataframe
                df = df.fillna("")

                for row_idx, row in df.iterrows():
                    # Convert row to text
                    row_text = " | ".join(str(v) for v in row.values if str(v).strip())
                    row_text = re.sub(r"\s+", " ", row_text).strip()

                    if len(row_text) < 10:
                        continue

                    # Truncate to default chunk size
                    row_text = row_text[:settings.chunk_size_default]

                    # Try to extract numeric value
                    numbers = re.findall(r"[\d,]+(?:\.\d+)?", row_text)
                    value = None
                    if numbers:
                        try:
                            # Take the largest number as the main value
                            value = max(float(n.replace(",", "")) for n in numbers)
                        except ValueError:
                            pass

                    node = Node(
                        id=self._generate_node_id(NodeType.TABLE_ROW),
                        type=NodeType.TABLE_ROW,
                        text=row_text,
                        metadata=NodeMetadata(
                            filing_id=self.filing_id,
                            period=self.period,
                            table_id=table_id,
                            row_index=int(row_idx),
                            value=value,
                        ),
                    )
                    nodes.append(node)

            except Exception as e:
                logger.debug(f"Could not parse table {table_idx}: {e}")
                continue

        return nodes

    def _extract_notes(self, soup: BeautifulSoup) -> list[Node]:
        """Extract footnotes/notes from the filing."""
        nodes = []

        text = soup.get_text(separator="\n", strip=True)

        # Find notes sections
        note_matches = list(re.finditer(self.NOTE_PATTERN, text, re.IGNORECASE | re.MULTILINE))

        for i, match in enumerate(note_matches):
            note_number = int(match.group(1))
            note_title = match.group(2).strip()

            # Find note content (text until next note or section)
            start_pos = match.end()
            if i + 1 < len(note_matches):
                end_pos = note_matches[i + 1].start()
            else:
                # Look for next Item section
                next_item = re.search(r"Item\s+\d+", text[start_pos:], re.IGNORECASE)
                if next_item:
                    end_pos = start_pos + next_item.start()
                else:
                    end_pos = min(start_pos + 5000, len(text))

            note_text = text[start_pos:end_pos].strip()

            # Skip very short notes
            if len(note_text) < settings.chunk_min_length:
                continue

            # Truncate to default chunk size (notes need good context)
            note_text = f"Note {note_number} - {note_title}\n{note_text}"[:settings.chunk_size_default]

            node = Node(
                id=self._generate_node_id(NodeType.NOTE),
                type=NodeType.NOTE,
                text=note_text,
                metadata=NodeMetadata(
                    filing_id=self.filing_id,
                    period=self.period,
                    section=f"Note {note_number}",
                    note_number=note_number,
                    char_offset=match.start(),
                ),
            )
            nodes.append(node)

        return nodes


def parse_filing(file_path: Path, filing_id: str, period: str) -> list[Node]:
    """Convenience function to parse a filing."""
    parser = HTMLParser(filing_id, period)
    return parser.parse_file(file_path)


if __name__ == "__main__":
    import sys
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    # Test with a sample file
    test_file = Path("data/raw/0000320193/000032019324000123/filing.html")
    if test_file.exists():
        nodes = parse_filing(test_file, "AAPL-10K-2024", "FY2024")
        logger.info(f"Parsed {len(nodes)} nodes")
        for node_type in NodeType:
            count = len([n for n in nodes if n.type == node_type])
            logger.info(f"  {node_type.value}: {count}")
    else:
        logger.warning(f"Test file not found: {test_file}")
