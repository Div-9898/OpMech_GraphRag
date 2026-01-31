#!/usr/bin/env python3
"""
Graph RAG Query System for Fundamental Analysis
Uses the knowledge graph to answer financial questions about Apple.
"""

import sys
import json
from typing import Optional
from neo4j import GraphDatabase
from openai import OpenAI

# Configuration
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"
VLLM_BASE_URL = "http://localhost:8000/v1"
MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"


def get_neo4j_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def search_graph(driver, query: str, limit: int = 20) -> dict:
    """Search the graph for nodes relevant to the query."""

    # Extract key terms from query
    search_terms = query.lower().split()
    financial_keywords = [
        "revenue", "sales", "net sales", "profit", "income", "margin",
        "cash", "debt", "assets", "liabilities", "equity", "eps",
        "operating", "gross", "net", "growth", "yoy", "quarter",
        "iphone", "mac", "ipad", "services", "wearables",
        "risk", "guidance", "outlook", "segment", "geographic"
    ]

    # Find matching keywords
    matched_terms = [t for t in search_terms if any(k in t for k in financial_keywords)]
    if not matched_terms:
        matched_terms = search_terms[:5]  # Use first 5 words as fallback

    with driver.session() as session:
        results = {
            "financial_data": [],
            "text_sections": [],
            "notes": [],
            "entities": [],
            "relationships": []
        }

        # Search for financial line items
        for term in matched_terms:
            result = session.run("""
                MATCH (n:Node {type: 'FINANCIAL_LINE'})
                WHERE toLower(n.text) CONTAINS $term
                RETURN n.id as id, n.text as text, n.filing_id as filing
                LIMIT 10
            """, term=term)
            for record in result:
                results["financial_data"].append({
                    "id": record["id"],
                    "text": record["text"],
                    "filing": record["filing"]
                })

        # Search text sections
        for term in matched_terms:
            result = session.run("""
                MATCH (n:Node {type: 'TEXT_SECTION'})
                WHERE toLower(n.text) CONTAINS $term
                RETURN n.id as id, n.text as text, n.filing_id as filing
                LIMIT 5
            """, term=term)
            for record in result:
                results["text_sections"].append({
                    "id": record["id"],
                    "text": record["text"][:500],  # Truncate long sections
                    "filing": record["filing"]
                })

        # Search notes
        for term in matched_terms:
            result = session.run("""
                MATCH (n:Node {type: 'NOTE'})
                WHERE toLower(n.text) CONTAINS $term
                RETURN n.id as id, n.text as text, n.filing_id as filing
                LIMIT 5
            """, term=term)
            for record in result:
                results["notes"].append({
                    "id": record["id"],
                    "text": record["text"][:500],
                    "filing": record["filing"]
                })

        # Get relevant entities
        result = session.run("""
            MATCH (n:Node {type: 'ENTITY'})
            WHERE toLower(n.text) CONTAINS 'apple'
               OR toLower(n.text) CONTAINS 'iphone'
               OR toLower(n.text) CONTAINS 'services'
               OR toLower(n.text) CONTAINS 'revenue'
            RETURN DISTINCT n.text as text
            LIMIT 10
        """)
        results["entities"] = [record["text"] for record in result]

        # Get some causal relationships
        result = session.run("""
            MATCH (s)-[r {expert: 'CausalChainBuilder'}]->(t)
            RETURN s.text as cause, t.text as effect, r.evidence as evidence
            LIMIT 5
        """)
        for record in result:
            results["relationships"].append({
                "cause": record["cause"][:200] if record["cause"] else "",
                "effect": record["effect"][:200] if record["effect"] else "",
                "evidence": record["evidence"]
            })

        # Deduplicate
        results["financial_data"] = list({r["text"]: r for r in results["financial_data"]}.values())[:15]
        results["text_sections"] = list({r["text"][:100]: r for r in results["text_sections"]}.values())[:5]
        results["notes"] = list({r["text"][:100]: r for r in results["notes"]}.values())[:5]

        return results


def get_temporal_data(driver, metric: str) -> list:
    """Get time-series data for a specific metric across filings."""
    with driver.session() as session:
        result = session.run("""
            MATCH (n:Node {type: 'FINANCIAL_LINE'})
            WHERE toLower(n.text) CONTAINS $metric
            RETURN n.text as text, n.filing_id as filing
            ORDER BY n.filing_id
        """, metric=metric.lower())
        return [{"text": r["text"], "filing": r["filing"]} for r in result]


def format_context(search_results: dict, temporal_data: list = None) -> str:
    """Format search results into context for the LLM."""
    context_parts = []

    context_parts.append("=== APPLE INC. FINANCIAL DATA FROM SEC FILINGS (2022-2024) ===\n")

    if search_results["financial_data"]:
        context_parts.append("## Financial Metrics:")
        for item in search_results["financial_data"]:
            context_parts.append(f"- {item['text']} (Source: {item['filing']})")

    if temporal_data:
        context_parts.append("\n## Time Series Data:")
        for item in temporal_data:
            context_parts.append(f"- {item['text']} ({item['filing']})")

    if search_results["text_sections"]:
        context_parts.append("\n## Management Discussion & Analysis:")
        for item in search_results["text_sections"]:
            context_parts.append(f"[{item['filing']}]: {item['text'][:300]}...")

    if search_results["notes"]:
        context_parts.append("\n## Financial Statement Notes:")
        for item in search_results["notes"]:
            context_parts.append(f"[{item['filing']}]: {item['text'][:300]}...")

    if search_results["relationships"]:
        context_parts.append("\n## Causal Relationships Identified:")
        for rel in search_results["relationships"]:
            context_parts.append(f"- Cause: {rel['cause'][:100]}...")
            context_parts.append(f"  Effect: {rel['effect'][:100]}...")

    return "\n".join(context_parts)


def query_llm(client: OpenAI, question: str, context: str) -> str:
    """Send query to LLM with graph context."""

    system_prompt = """You are a financial analyst assistant with access to Apple Inc.'s SEC filings data (10-K and 10-Q reports from 2022-2024).

Your task is to answer fundamental analysis questions using ONLY the provided context from the knowledge graph.

Guidelines:
- Be specific and cite the source filings when possible
- If the data shows trends, highlight them
- If information is not available in the context, say so
- Provide quantitative data when available
- Keep your answer concise but comprehensive"""

    user_prompt = f"""Question: {question}

Context from Apple SEC Filings Knowledge Graph:
{context}

Please provide a detailed answer based on the above context."""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=1024,
        temperature=0.3
    )

    return response.choices[0].message.content


def run_query(question: str) -> str:
    """Run a complete Graph RAG query."""
    print(f"\n{'='*60}")
    print(f"Question: {question}")
    print('='*60)

    # Initialize connections
    driver = get_neo4j_driver()
    client = OpenAI(base_url=VLLM_BASE_URL, api_key="not-needed")

    try:
        # Search the graph
        print("\n[1/3] Searching knowledge graph...")
        search_results = search_graph(driver, question)

        # Get temporal data for key metrics
        print("[2/3] Retrieving temporal trends...")
        temporal_data = []
        if "revenue" in question.lower() or "sales" in question.lower():
            temporal_data = get_temporal_data(driver, "net sales")
        elif "profit" in question.lower() or "income" in question.lower():
            temporal_data = get_temporal_data(driver, "net income")
        elif "cash" in question.lower():
            temporal_data = get_temporal_data(driver, "cash")

        # Format context
        context = format_context(search_results, temporal_data)

        print(f"\n[Context Summary]")
        print(f"  - Financial items found: {len(search_results['financial_data'])}")
        print(f"  - Text sections found: {len(search_results['text_sections'])}")
        print(f"  - Notes found: {len(search_results['notes'])}")
        print(f"  - Temporal data points: {len(temporal_data)}")

        # Query LLM
        print("\n[3/3] Generating answer with LLM...")
        answer = query_llm(client, question, context)

        return answer

    finally:
        driver.close()


# Example queries for fundamental analysis
EXAMPLE_QUERIES = [
    "What was Apple's revenue trend from 2022 to 2024?",
    "How did Apple's Services segment perform compared to iPhone sales?",
    "What are the main risk factors mentioned in Apple's filings?",
    "What is Apple's gross margin and how has it changed?",
    "How much cash does Apple have and what is their capital allocation strategy?",
]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Use command line argument as question
        question = " ".join(sys.argv[1:])
    else:
        # Interactive mode
        print("\n" + "="*60)
        print("GRAPH RAG - Apple Fundamental Analysis")
        print("="*60)
        print("\nExample queries:")
        for i, q in enumerate(EXAMPLE_QUERIES, 1):
            print(f"  {i}. {q}")

        print("\nEnter your question (or number 1-5 for examples, 'q' to quit):")

        while True:
            try:
                user_input = input("\n> ").strip()

                if user_input.lower() == 'q':
                    print("Goodbye!")
                    break

                if user_input.isdigit() and 1 <= int(user_input) <= len(EXAMPLE_QUERIES):
                    question = EXAMPLE_QUERIES[int(user_input) - 1]
                else:
                    question = user_input

                if question:
                    answer = run_query(question)
                    print("\n" + "-"*60)
                    print("ANSWER:")
                    print("-"*60)
                    print(answer)

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
