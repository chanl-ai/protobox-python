"""Enhanced embedding service supporting multiple providers with LangChain integration."""

from typing import Any

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from loguru import logger

from protobox.admin.config import settings


class EmbeddingService:
    """Enhanced service for generating embeddings with LangChain integration."""

    def __init__(self, provider: str | None = None, model: str | None = None, api_key: str | None = None):
        """
        Initialize embedding service with LangChain integration.
        
        Args:
            provider: Embedding provider ('openai' or 'huggingface')
            model: Model name to use
            api_key: API key (for OpenAI)
        """
        self.provider = provider or settings.embedding_provider
        self.api_key = api_key or settings.openai_api_key
        self.model = model

        # Initialize LangChain embeddings based on provider
        if self.provider == "openai":
            if not self.api_key:
                raise ValueError("OpenAI API key required for OpenAI provider")

            self.model = model or settings.embedding_model
            self.langchain_embeddings: Embeddings = OpenAIEmbeddings(
                model=self.model,
                api_key=self.api_key,
                chunk_size=1000,
                max_retries=3,
                timeout=60.0
            )

            self.max_tokens = 8192
            self.dimensions = 1536 if "small" in self.model else 3072

        elif self.provider == "huggingface":
            self.model = model or settings.huggingface_model
            self.langchain_embeddings: Embeddings = HuggingFaceEmbeddings(
                model_name=self.model,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )

            self.max_tokens = 512
            self.dimensions = None  # Will be determined from first embedding

        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")

        logger.info(f"Initialized EmbeddingService with LangChain provider: {self.provider}, model: {self.model}")

    async def generate_embedding(self, text: str, model: str | None = None) -> list[float]:
        """
        Generate embedding for a single text using LangChain.

        Args:
            text: Text to embed
            model: Optional model override (maintained for compatibility)

        Returns:
            List of float values representing the embedding
        """
        if not text.strip():
            raise ValueError("Text cannot be empty")

        # Truncate text if too long
        if len(text) > self.max_tokens:
            text = text[:self.max_tokens]
            logger.warning(f"Text truncated to {self.max_tokens} characters for embedding")

        try:
            # Use LangChain's async embedding generation
            embedding = await self.langchain_embeddings.aembed_query(text)

            # Set dimensions on first use for HuggingFace
            if self.dimensions is None:
                self.dimensions = len(embedding)
                logger.info(f"Set embedding dimensions: {self.dimensions}")

            logger.debug(f"Generated LangChain embedding with {len(embedding)} dimensions")
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate LangChain embedding: {e}")
            raise


    async def generate_embeddings_batch(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batch using LangChain.

        Args:
            texts: List of texts to embed
            model: Optional model override (maintained for compatibility)

        Returns:
            List of embeddings corresponding to input texts
        """
        if not texts:
            return []

        # Filter out empty texts
        valid_texts = [(i, text) for i, text in enumerate(texts) if text.strip()]
        if not valid_texts:
            raise ValueError("No valid texts to embed")

        # Truncate texts if needed
        processed_texts = []
        for i, text in valid_texts:
            if len(text) > self.max_tokens:
                text = text[:self.max_tokens]
                logger.warning(f"Text {i} truncated to {self.max_tokens} characters")
            processed_texts.append(text)

        try:
            # Use LangChain's batch embedding generation
            embeddings = await self.langchain_embeddings.aembed_documents(processed_texts)

            # Set dimensions on first use for HuggingFace
            if self.dimensions is None and embeddings:
                self.dimensions = len(embeddings[0])
                logger.info(f"Set embedding dimensions: {self.dimensions}")

            logger.info(f"Generated {len(embeddings)} embeddings in batch using LangChain")

            # Map back to original indices (handle empty texts)
            result = [None] * len(texts)
            for (original_idx, _), embedding in zip(valid_texts, embeddings, strict=False):
                result[original_idx] = embedding

            return result

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings with LangChain: {e}")
            raise



    def get_embedding_model_info(self) -> dict[str, Any]:
        """Get information about the current embedding model."""
        base_info = {
            "provider": self.provider,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "dimensions": self.dimensions,
            "langchain_enabled": True
        }

        if self.provider == "openai":
            base_info.update({
                "cost_per_1k_tokens": 0.00002 if "small" in self.model else 0.00013,
                "api_required": True,
                "langchain_class": "OpenAIEmbeddings"
            })
        elif self.provider == "huggingface":
            base_info.update({
                "cost_per_1k_tokens": 0.0,  # Free
                "api_required": False,
                "local_model": True,
                "langchain_class": "HuggingFaceEmbeddings"
            })

        return base_info

    def get_langchain_embeddings(self) -> Embeddings:
        """Get the underlying LangChain Embeddings instance for advanced use."""
        return self.langchain_embeddings
