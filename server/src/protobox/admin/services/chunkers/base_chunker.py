"""Base chunker class for content processing strategies."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

logger = logging.getLogger(__name__)


class ChunkedContent:
    """Container for chunked content with metadata."""

    def __init__(self, chunks: list[dict[str, Any]], metadata: dict[str, Any]):
        self.chunks = chunks
        self.metadata = metadata
        self.created_at = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'chunks': self.chunks,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }


class BaseChunker(ABC):
    """Base class for all chunking strategies."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50, encoding_name: str = "cl100k_base"):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker_name = self.__class__.__name__

        # Initialize tokenizer if available
        self.tokenizer = None
        if TIKTOKEN_AVAILABLE:
            try:
                self.tokenizer = tiktoken.get_encoding(encoding_name)
            except Exception as e:
                logger.warning(f"Failed to initialize tokenizer: {e}")

        logger.info(f"Initialized {self.chunker_name} with chunk_size={chunk_size}, overlap={chunk_overlap}")

    @abstractmethod
    async def chunk(self, content: str, **kwargs) -> ChunkedContent:
        """
        Chunk content according to the strategy.
        
        Args:
            content: Content to chunk
            **kwargs: Strategy-specific options
            
        Returns:
            ChunkedContent with chunks and metadata
        """
        pass

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        # Fallback: rough estimate (1 token ≈ 4 characters)
        return len(text) // 4

    def split_by_tokens(self, text: str, max_tokens: int, overlap_tokens: int = 0) -> list[str]:
        """Split text by token count."""
        if not text.strip():
            return []

        if self.tokenizer:
            tokens = self.tokenizer.encode(text)
            chunks = []

            start = 0
            while start < len(tokens):
                end = min(start + max_tokens, len(tokens))
                chunk_tokens = tokens[start:end]
                chunk_text = self.tokenizer.decode(chunk_tokens)
                chunks.append(chunk_text)

                if end >= len(tokens):
                    break

                start = end - overlap_tokens

            return chunks
        # Fallback: split by character count
        char_limit = max_tokens * 4  # Rough estimate
        overlap_chars = overlap_tokens * 4

        chunks = []
        start = 0
        while start < len(text):
            end = min(start + char_limit, len(text))
            chunk = text[start:end]
            chunks.append(chunk)

            if end >= len(text):
                break

            start = end - overlap_chars

        return chunks

    def split_by_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        import re

        # Simple sentence splitting
        sentences = re.split(r'[.!?]+\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Handle edge cases where split removes the ending punctuation
        result = []
        for i, sentence in enumerate(sentences):
            if i < len(sentences) - 1 and not sentence.endswith(('.', '!', '?')):
                # Find the original punctuation
                original_pos = text.find(sentence) + len(sentence)
                if original_pos < len(text) and text[original_pos] in '.!?':
                    sentence += text[original_pos]
            result.append(sentence)

        return result

    def split_by_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs."""
        paragraphs = text.split('\n\n')
        return [p.strip() for p in paragraphs if p.strip()]

    def create_chunk(
        self,
        content: str,
        chunk_index: int,
        chunk_type: str = "content",
        source_metadata: dict[str, Any] | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """Create a standardized chunk dictionary."""
        chunk = {
            'content': content.strip(),
            'chunk_index': chunk_index,
            'chunk_type': chunk_type,
            'token_count': self.count_tokens(content),
            'character_count': len(content),
            'source_metadata': source_metadata or {},
            'chunker': self.chunker_name,
            'chunk_size_limit': self.chunk_size,
            'created_at': datetime.utcnow().isoformat()
        }

        # Add any additional metadata
        chunk.update(kwargs)

        return chunk

    def create_base_metadata(self, content: str, strategy_specific: dict[str, Any] | None = None) -> dict[str, Any]:
        """Create base metadata for chunked content."""
        metadata = {
            'chunker': self.chunker_name,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'original_content_length': len(content),
            'original_token_count': self.count_tokens(content),
            'tokenizer_available': self.tokenizer is not None,
            'processing_timestamp': datetime.utcnow().isoformat()
        }

        if strategy_specific:
            metadata.update(strategy_specific)

        return metadata

    def merge_overlapping_chunks(self, chunks: list[str], overlap_ratio: float = 0.3) -> list[str]:
        """Merge chunks that have significant overlap."""
        if not chunks or len(chunks) < 2:
            return chunks

        merged = [chunks[0]]

        for current_chunk in chunks[1:]:
            last_chunk = merged[-1]

            # Check for overlap by looking at the beginning of current and end of last
            overlap_length = min(len(last_chunk), len(current_chunk)) // 2

            last_end = last_chunk[-overlap_length:]
            current_start = current_chunk[:overlap_length]

            # Simple overlap detection (can be improved)
            common_words = set(last_end.split()) & set(current_start.split())

            if len(common_words) / max(len(last_end.split()), len(current_start.split())) > overlap_ratio:
                # Merge chunks
                merged[-1] = last_chunk + " " + current_chunk
            else:
                merged.append(current_chunk)

        return merged

    def clean_chunk_content(self, content: str) -> str:
        """Clean and normalize chunk content."""
        # Remove excessive whitespace
        import re
        content = re.sub(r'\s+', ' ', content)

        # Remove leading/trailing whitespace
        content = content.strip()

        # Remove very short lines that might be artifacts
        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if len(line) > 3 or not line:  # Keep empty lines for structure
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines).strip()

    def calculate_chunk_quality_score(self, chunk: str) -> float:
        """Calculate a quality score for a chunk (0-1)."""
        if not chunk.strip():
            return 0.0

        score = 1.0

        # Penalize very short chunks
        if len(chunk) < 50:
            score *= 0.5

        # Penalize chunks that are mostly punctuation or numbers
        alpha_chars = sum(1 for c in chunk if c.isalpha())
        if alpha_chars / len(chunk) < 0.3:
            score *= 0.3

        # Reward chunks with complete sentences
        sentences = self.split_by_sentences(chunk)
        if len(sentences) >= 1:
            complete_sentences = sum(1 for s in sentences if s.endswith(('.', '!', '?')))
            score *= (complete_sentences / len(sentences)) * 0.5 + 0.5

        # Reward balanced token count
        token_count = self.count_tokens(chunk)
        if self.chunk_size * 0.3 <= token_count <= self.chunk_size:
            score *= 1.0
        elif token_count < self.chunk_size * 0.3:
            score *= 0.7
        else:
            score *= 0.9  # Slightly penalize oversized chunks

        return min(1.0, score)
