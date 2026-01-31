"""Configuration management for MoE Graph Builder."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Neo4j
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="password123")

    # SEC EDGAR
    sec_user_agent: str = Field(default="MoEGraphBuilder research@example.com")
    sec_rate_limit: float = Field(default=10.0)  # requests per second
    sec_base_url: str = Field(default="https://data.sec.gov")
    sec_archive_url: str = Field(default="https://www.sec.gov")
    # NOTE: CIK is now dynamically resolved via CompanyConfig.from_ticker()
    # The apple_cik field is deprecated - use CompanyConfig instead
    default_ticker: str = Field(default="AAPL")  # Default company for backwards compatibility

    # vLLM
    vllm_api_base: str = Field(default="http://localhost:8000/v1")
    vllm_model: str = Field(default="Qwen/Qwen2.5-7B-Instruct")
    vllm_max_tokens: int = Field(default=1024)
    vllm_temperature: float = Field(default=0.1)

    # Embeddings
    finbert_model: str = Field(default="ProsusAI/finbert")
    embedding_batch_size: int = Field(default=32)
    embedding_max_length: int = Field(default=512)
    device: Literal["cuda", "cpu", "mps"] = Field(default="cuda")

    # Paths
    data_dir: Path = Field(default=Path("./data"))
    raw_dir: Path = Field(default=Path("./data/raw"))
    parsed_dir: Path = Field(default=Path("./data/parsed"))
    embeddings_dir: Path = Field(default=Path("./data/embeddings"))
    gold_dir: Path = Field(default=Path("./data/gold"))

    # Processing
    batch_size: int = Field(default=32)
    max_workers: int = Field(default=4)

    # Chunking settings
    chunk_size_default: int = Field(default=5000)  # Default max chars per chunk
    chunk_size_mda: int = Field(default=8000)  # MD&A (Item 7) - more context needed
    chunk_size_risk: int = Field(default=8000)  # Risk Factors (Item 1A) - more context needed
    chunk_min_length: int = Field(default=50)  # Minimum paragraph length

    # Expert thresholds
    cross_ref_confidence_threshold: float = Field(default=0.5)
    causal_confidence_threshold: float = Field(default=0.5)
    temporal_similarity_threshold: float = Field(default=0.90)
    table_text_similarity_threshold: float = Field(default=0.80)
    semantic_similarity_threshold: float = Field(default=0.85)
    bridge_similarity_threshold: float = Field(default=0.70)

    def ensure_dirs(self) -> None:
        """Create data directories if they don't exist."""
        for dir_path in [
            self.data_dir,
            self.raw_dir,
            self.parsed_dir,
            self.embeddings_dir,
            self.gold_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()


# NOTE: Company-specific filing configurations have been removed.
# Fiscal periods are now computed dynamically based on CompanyConfig.fiscal_year_end_month.
# Use CompanyConfig.format_fiscal_period() to generate period labels.
#
# Example usage:
#   from src.company_config import CompanyConfig
#   config = CompanyConfig.from_ticker("AAPL")
#   period_label = config.format_fiscal_period("2024-09-28", "10-K")  # Returns "FY2024"
