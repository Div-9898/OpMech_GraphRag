"""Embedding engine using FinBERT for generating node embeddings."""

import json
from pathlib import Path
from typing import Generator

import numpy as np
import torch
from loguru import logger
from tqdm import tqdm
from transformers import AutoModel, AutoTokenizer

from src.config import settings
from src.models import Node


class EmbeddingEngine:
    """Generates embeddings for nodes using FinBERT."""

    def __init__(
        self,
        model_name: str = None,
        device: str = None,
        batch_size: int = None,
        max_length: int = None,
    ):
        self.model_name = model_name or settings.finbert_model
        self.device = device or settings.device
        self.batch_size = batch_size or settings.embedding_batch_size
        self.max_length = max_length or settings.embedding_max_length

        self.tokenizer = None
        self.model = None
        self._loaded = False

    def load(self) -> None:
        """Load the FinBERT model and tokenizer."""
        if self._loaded:
            return

        logger.info(f"Loading FinBERT model: {self.model_name}")
        logger.info(f"Device: {self.device}")

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()

        self._loaded = True
        logger.info("FinBERT model loaded successfully")

    def unload(self) -> None:
        """Unload the model to free memory."""
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        self._loaded = False

        if self.device == "cuda":
            torch.cuda.empty_cache()

    def _mean_pooling(self, model_output: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        """Apply mean pooling to get sentence embeddings."""
        token_embeddings = model_output[0]  # First element is the hidden states
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(
            input_mask_expanded.sum(1), min=1e-9
        )

    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        self.load()

        # Tokenize
        encoded = self.tokenizer(
            text,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )

        # Move to device
        encoded = {k: v.to(self.device) for k, v in encoded.items()}

        # Generate embedding
        with torch.no_grad():
            output = self.model(**encoded)
            embedding = self._mean_pooling(output, encoded["attention_mask"])
            embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)

        return embedding.cpu().numpy()[0]

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for a batch of texts."""
        self.load()

        # Tokenize
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )

        # Move to device
        encoded = {k: v.to(self.device) for k, v in encoded.items()}

        # Generate embeddings
        with torch.no_grad():
            output = self.model(**encoded)
            embeddings = self._mean_pooling(output, encoded["attention_mask"])
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

        return embeddings.cpu().numpy()

    def embed_nodes(
        self,
        nodes: list[Node],
        show_progress: bool = True,
    ) -> dict[str, np.ndarray]:
        """
        Generate embeddings for a list of nodes.

        Args:
            nodes: List of Node objects
            show_progress: Whether to show progress bar

        Returns:
            Dictionary mapping node_id -> embedding
        """
        self.load()

        embeddings = {}
        texts = [node.text for node in nodes]
        ids = [node.id for node in nodes]

        # Process in batches
        iterator = range(0, len(texts), self.batch_size)
        if show_progress:
            iterator = tqdm(iterator, desc="Generating embeddings", unit="batch")

        for i in iterator:
            batch_texts = texts[i : i + self.batch_size]
            batch_ids = ids[i : i + self.batch_size]

            batch_embeddings = self.embed_batch(batch_texts)

            for node_id, embedding in zip(batch_ids, batch_embeddings):
                embeddings[node_id] = embedding

        logger.info(f"Generated {len(embeddings)} embeddings")
        return embeddings

    def save_embeddings(
        self,
        embeddings: dict[str, np.ndarray],
        output_path: Path,
    ) -> None:
        """Save embeddings to a numpy file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save as npz file
        np.savez_compressed(output_path, **embeddings)
        logger.info(f"Saved {len(embeddings)} embeddings to {output_path}")

        # Also save a mapping file
        mapping_path = output_path.with_suffix(".json")
        mapping = {node_id: i for i, node_id in enumerate(embeddings.keys())}
        mapping_path.write_text(json.dumps(mapping, indent=2))

    def load_embeddings(self, input_path: Path) -> dict[str, np.ndarray]:
        """Load embeddings from a numpy file."""
        input_path = Path(input_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Embeddings file not found: {input_path}")

        data = np.load(input_path)
        embeddings = {key: data[key] for key in data.files}

        logger.info(f"Loaded {len(embeddings)} embeddings from {input_path}")
        return embeddings


def compute_cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """Compute cosine similarity between two embeddings."""
    return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))


def find_similar_nodes(
    query_embedding: np.ndarray,
    embeddings: dict[str, np.ndarray],
    top_k: int = 10,
    threshold: float = 0.0,
) -> list[tuple[str, float]]:
    """
    Find nodes most similar to a query embedding.

    Args:
        query_embedding: Query embedding vector
        embeddings: Dictionary of node_id -> embedding
        top_k: Number of results to return
        threshold: Minimum similarity threshold

    Returns:
        List of (node_id, similarity) tuples, sorted by similarity
    """
    similarities = []

    for node_id, embedding in embeddings.items():
        sim = compute_cosine_similarity(query_embedding, embedding)
        if sim >= threshold:
            similarities.append((node_id, sim))

    # Sort by similarity descending
    similarities.sort(key=lambda x: x[1], reverse=True)

    return similarities[:top_k]


# Global engine instance (lazy loaded)
_engine: EmbeddingEngine | None = None


def get_engine() -> EmbeddingEngine:
    """Get or create the global embedding engine."""
    global _engine
    if _engine is None:
        _engine = EmbeddingEngine()
    return _engine


if __name__ == "__main__":
    import sys
    from loguru import logger

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    # Test the embedding engine
    engine = EmbeddingEngine()

    test_texts = [
        "Apple Inc. reported revenue of $383.3 billion for fiscal year 2024.",
        "The company's iPhone segment generated $200.6 billion in net sales.",
        "Research and development expenses increased due to headcount growth.",
        "Management believes supply chain constraints may impact future revenue.",
    ]

    logger.info("Testing embedding generation...")

    # Generate embeddings
    embeddings = engine.embed_batch(test_texts)
    logger.info(f"Generated {len(embeddings)} embeddings of shape {embeddings[0].shape}")

    # Test similarity
    logger.info("\nSimilarity matrix:")
    for i, text1 in enumerate(test_texts):
        sims = []
        for j, text2 in enumerate(test_texts):
            sim = compute_cosine_similarity(embeddings[i], embeddings[j])
            sims.append(f"{sim:.3f}")
        logger.info(f"  [{', '.join(sims)}]")

    # Cleanup
    engine.unload()
    logger.info("\nTest completed successfully")
