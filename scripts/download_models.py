#!/usr/bin/env python3
"""
Download required ML models for the MoE Graph Builder.

This script downloads models ONLY after user confirmation.
Models are cached locally in ~/.cache/huggingface/ and ~/.cache/torch/

Required Models:
1. FinBERT (ProsusAI/finbert) - ~420MB - For generating embeddings
2. spaCy en_core_web_lg - ~560MB - For NLP tasks (dependency parsing)

Optional Models (for LLM-based causal extraction):
3. Qwen/Qwen3-8B or mistralai/Mistral-7B-Instruct-v0.3 - ~16GB each

Usage:
    python scripts/download_models.py --finbert          # Download FinBERT only
    python scripts/download_models.py --spacy            # Download spaCy model only
    python scripts/download_models.py --all-required     # Download all required models
    python scripts/download_models.py --llm qwen         # Download Qwen3-8B
    python scripts/download_models.py --llm mistral      # Download Mistral-7B
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


def setup_logging():
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")


def download_finbert():
    """Download FinBERT model for embeddings."""
    logger.info("Downloading FinBERT (ProsusAI/finbert)...")
    logger.info("  Size: ~420MB")
    logger.info("  Purpose: Generate 768-dim embeddings for financial text")

    try:
        from transformers import AutoModel, AutoTokenizer

        model_name = "ProsusAI/finbert"
        logger.info(f"  Loading tokenizer from {model_name}...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)

        logger.info(f"  Loading model from {model_name}...")
        model = AutoModel.from_pretrained(model_name)

        logger.info("  FinBERT downloaded successfully!")
        return True
    except Exception as e:
        logger.error(f"  Failed to download FinBERT: {e}")
        return False


def download_spacy():
    """Download spaCy English model."""
    logger.info("Downloading spaCy en_core_web_lg...")
    logger.info("  Size: ~560MB")
    logger.info("  Purpose: Dependency parsing for causal extraction")

    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "spacy", "download", "en_core_web_lg"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            logger.info("  spaCy model downloaded successfully!")
            return True
        else:
            logger.error(f"  Failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"  Failed to download spaCy model: {e}")
        return False


def download_llm(model_choice: str):
    """Download LLM model for vLLM inference."""
    models = {
        "qwen": "Qwen/Qwen2.5-7B-Instruct",
        "mistral": "mistralai/Mistral-7B-Instruct-v0.3",
    }

    if model_choice not in models:
        logger.error(f"Unknown model: {model_choice}. Choose from: {list(models.keys())}")
        return False

    model_name = models[model_choice]
    logger.info(f"Downloading {model_name}...")
    logger.info("  Size: ~16GB")
    logger.info("  Purpose: LLM-based causal relationship extraction")
    logger.info("  Note: This model runs via vLLM server, not loaded directly")

    try:
        from huggingface_hub import snapshot_download

        logger.info(f"  Downloading from Hugging Face Hub...")
        snapshot_download(repo_id=model_name)

        logger.info(f"  {model_name} downloaded successfully!")
        return True
    except Exception as e:
        logger.error(f"  Failed to download {model_name}: {e}")
        logger.info("  You can download manually later with:")
        logger.info(f"    huggingface-cli download {model_name}")
        return False


def check_models():
    """Check which models are already downloaded."""
    logger.info("Checking installed models...")

    # Check FinBERT
    try:
        from transformers import AutoConfig
        AutoConfig.from_pretrained("ProsusAI/finbert", local_files_only=True)
        logger.info("  [OK] FinBERT is installed")
    except:
        logger.info("  [--] FinBERT not found")

    # Check spaCy
    try:
        import spacy
        spacy.load("en_core_web_lg")
        logger.info("  [OK] spaCy en_core_web_lg is installed")
    except:
        logger.info("  [--] spaCy en_core_web_lg not found")

    # Check LLMs
    try:
        from huggingface_hub import scan_cache_dir
        cache = scan_cache_dir()
        llm_models = ["Qwen/Qwen3-8B", "mistralai/Mistral-7B-Instruct-v0.3"]
        for model in llm_models:
            found = any(repo.repo_id == model for repo in cache.repos)
            status = "[OK]" if found else "[--]"
            logger.info(f"  {status} {model}")
    except:
        pass


def main():
    parser = argparse.ArgumentParser(description="Download ML models for MoE Graph Builder")
    parser.add_argument("--finbert", action="store_true", help="Download FinBERT")
    parser.add_argument("--spacy", action="store_true", help="Download spaCy en_core_web_lg")
    parser.add_argument("--all-required", action="store_true", help="Download all required models")
    parser.add_argument("--llm", choices=["qwen", "mistral"], help="Download LLM model")
    parser.add_argument("--check", action="store_true", help="Check installed models")
    args = parser.parse_args()

    setup_logging()

    if args.check:
        check_models()
        return 0

    if not any([args.finbert, args.spacy, args.all_required, args.llm]):
        parser.print_help()
        logger.info("\n\nRecommended: python scripts/download_models.py --all-required")
        return 0

    success = True

    if args.finbert or args.all_required:
        success &= download_finbert()

    if args.spacy or args.all_required:
        success &= download_spacy()

    if args.llm:
        success &= download_llm(args.llm)

    if success:
        logger.info("\nAll requested models downloaded successfully!")
    else:
        logger.warning("\nSome models failed to download. Check errors above.")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
