"""Smart chunker with topic-based clustering."""

import asyncio
import logging
import re
from collections import defaultdict
from typing import Any

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
    CLUSTERING_AVAILABLE = True
except ImportError:
    CLUSTERING_AVAILABLE = False

from protobox.admin.config import settings

from .base_chunker import BaseChunker, ChunkedContent

logger = logging.getLogger(__name__)


class SmartChunker(BaseChunker):
    """Smart chunker that groups content by topic using semantic similarity."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50, **kwargs):
        super().__init__(chunk_size, chunk_overlap)

        self.use_clustering = CLUSTERING_AVAILABLE and settings.embedding_provider == "huggingface"
        self.sentence_model = None

        # Smart chunking parameters
        self.min_cluster_size = kwargs.get('min_cluster_size', 2)
        self.max_clusters = kwargs.get('max_clusters', 10)
        self.similarity_threshold = kwargs.get('similarity_threshold', 0.7)

        if self.use_clustering:
            logger.info("Smart chunker will use semantic clustering")
        else:
            logger.info("Smart chunker will use rule-based approach (clustering dependencies not available)")

    async def _get_sentence_model(self):
        """Lazy load sentence transformer model."""
        if self.sentence_model is None and self.use_clustering:
            loop = asyncio.get_event_loop()
            model_name = settings.huggingface_model
            self.sentence_model = await loop.run_in_executor(
                None,
                SentenceTransformer,
                model_name
            )
            logger.info(f"Loaded sentence model: {model_name}")
        return self.sentence_model

    async def chunk(self, content: str, **kwargs) -> ChunkedContent:
        """
        Chunk content using smart topic-based approach.
        
        Args:
            content: Content to chunk
            **kwargs: Additional options
            
        Returns:
            ChunkedContent with semantically grouped chunks
        """
        if not content.strip():
            return ChunkedContent([], self.create_base_metadata(content))

        try:
            if self.use_clustering:
                chunks = await self._semantic_chunking(content, **kwargs)
            else:
                chunks = await self._rule_based_chunking(content, **kwargs)

            # Calculate quality scores for chunks
            for chunk in chunks:
                chunk['quality_score'] = self.calculate_chunk_quality_score(chunk['content'])

            metadata = self.create_base_metadata(content, {
                'chunking_method': 'semantic' if self.use_clustering else 'rule_based',
                'total_chunks': len(chunks),
                'clustering_available': CLUSTERING_AVAILABLE,
                'average_chunk_size': sum(chunk['token_count'] for chunk in chunks) / len(chunks) if chunks else 0,
                'average_quality_score': sum(chunk['quality_score'] for chunk in chunks) / len(chunks) if chunks else 0
            })

            logger.info(f"Smart chunking created {len(chunks)} chunks using {'semantic' if self.use_clustering else 'rule-based'} approach")

            return ChunkedContent(chunks, metadata)

        except Exception as e:
            logger.error(f"Smart chunking failed: {e}")
            # Fallback to basic chunking
            return await self._fallback_chunking(content)

    async def _semantic_chunking(self, content: str, **kwargs) -> list[dict[str, Any]]:
        """Perform semantic chunking using sentence embeddings and clustering."""
        # Split content into sentences
        sentences = self.split_by_sentences(content)

        if len(sentences) < 2:
            # Not enough sentences for clustering
            return await self._rule_based_chunking(content, **kwargs)

        try:
            # Get sentence embeddings
            model = await self._get_sentence_model()
            loop = asyncio.get_event_loop()

            embeddings = await loop.run_in_executor(
                None,
                model.encode,
                sentences,
                {'convert_to_tensor': True, 'normalize_embeddings': True}
            )

            # Convert to numpy array
            embeddings_np = embeddings.cpu().numpy()

            # Determine optimal number of clusters
            n_clusters = min(self.max_clusters, max(2, len(sentences) // 5))

            # Perform clustering
            kmeans = await loop.run_in_executor(
                None,
                KMeans,
                n_clusters,
                42  # random_state
            )
            await loop.run_in_executor(None, kmeans.fit, embeddings_np)

            # Group sentences by cluster
            clusters = defaultdict(list)
            for i, (sentence, cluster_id) in enumerate(zip(sentences, kmeans.labels_, strict=False)):
                clusters[cluster_id].append((i, sentence))

            # Create chunks from clusters
            chunks = []
            for cluster_id, cluster_sentences in clusters.items():
                # Sort sentences by original order
                cluster_sentences.sort(key=lambda x: x[0])

                # Combine sentences in cluster
                cluster_text = ' '.join(sentence for _, sentence in cluster_sentences)

                # Split cluster if it's too large
                cluster_chunks = await self._split_large_cluster(cluster_text, cluster_id)
                chunks.extend(cluster_chunks)

            # Sort chunks by average sentence position to maintain some order
            chunks.sort(key=lambda x: x.get('average_position', 0))

            # Reindex chunks
            for i, chunk in enumerate(chunks):
                chunk['chunk_index'] = i

            return chunks

        except Exception as e:
            logger.warning(f"Semantic clustering failed: {e}, falling back to rule-based")
            return await self._rule_based_chunking(content, **kwargs)

    async def _split_large_cluster(self, cluster_text: str, cluster_id: int) -> list[dict[str, Any]]:
        """Split a large cluster into smaller chunks."""
        token_count = self.count_tokens(cluster_text)

        if token_count <= self.chunk_size:
            # Cluster fits in one chunk
            sentences = self.split_by_sentences(cluster_text)
            avg_position = sum(i for i in range(len(sentences))) / len(sentences) if sentences else 0

            return [self.create_chunk(
                content=cluster_text,
                chunk_index=0,  # Will be reindexed later
                chunk_type="semantic_cluster",
                source_metadata={
                    'cluster_id': cluster_id,
                    'sentence_count': len(sentences),
                    'average_position': avg_position
                }
            )]
        # Split cluster into smaller chunks
        sub_chunks = self.split_by_tokens(cluster_text, self.chunk_size, self.chunk_overlap)

        result = []
        for i, sub_chunk in enumerate(sub_chunks):
            chunk = self.create_chunk(
                content=sub_chunk,
                chunk_index=0,  # Will be reindexed later
                chunk_type="semantic_cluster_split",
                source_metadata={
                    'cluster_id': cluster_id,
                    'sub_chunk_index': i,
                    'total_sub_chunks': len(sub_chunks)
                }
            )
            result.append(chunk)

        return result

    async def _rule_based_chunking(self, content: str, **kwargs) -> list[dict[str, Any]]:
        """Fallback rule-based chunking using structure and boundaries."""
        chunks = []

        # First, try to split by structural elements
        structural_chunks = await self._split_by_structure(content)

        for i, chunk_text in enumerate(structural_chunks):
            token_count = self.count_tokens(chunk_text)

            if token_count <= self.chunk_size:
                # Chunk is appropriate size
                chunk = self.create_chunk(
                    content=chunk_text,
                    chunk_index=i,
                    chunk_type="structural",
                    source_metadata={'splitting_method': 'structural'}
                )
                chunks.append(chunk)
            else:
                # Split large chunk by sentences, then by tokens if needed
                sentence_chunks = await self._split_by_sentence_boundaries(chunk_text)

                for j, sentence_chunk in enumerate(sentence_chunks):
                    chunk = self.create_chunk(
                        content=sentence_chunk,
                        chunk_index=len(chunks),
                        chunk_type="sentence_boundary",
                        source_metadata={
                            'splitting_method': 'sentence_boundary',
                            'parent_structural_chunk': i,
                            'sentence_chunk_index': j
                        }
                    )
                    chunks.append(chunk)

        return chunks

    async def _split_by_structure(self, content: str) -> list[str]:
        """Split content by structural elements (headings, paragraphs, etc.)."""
        # Split by markdown headings first
        heading_pattern = r'^#{1,6}\s+.+$'
        lines = content.split('\n')

        chunks = []
        current_chunk = []

        for line in lines:
            if re.match(heading_pattern, line.strip()):
                # Start new chunk at heading
                if current_chunk:
                    chunks.append('\n'.join(current_chunk).strip())
                current_chunk = [line]
            else:
                current_chunk.append(line)

        # Add final chunk
        if current_chunk:
            chunks.append('\n'.join(current_chunk).strip())

        # If no headings found, split by double newlines (paragraphs)
        if len(chunks) <= 1:
            chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip()]

        return chunks

    async def _split_by_sentence_boundaries(self, content: str) -> list[str]:
        """Split content by sentence boundaries while respecting token limits."""
        sentences = self.split_by_sentences(content)

        if not sentences:
            return [content]

        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

            # If adding this sentence would exceed limit, start new chunk
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)

                # Start new chunk with overlap
                overlap_sentences = []
                overlap_tokens = 0

                # Add sentences from the end for overlap
                for prev_sentence in reversed(current_chunk):
                    prev_tokens = self.count_tokens(prev_sentence)
                    if overlap_tokens + prev_tokens <= self.chunk_overlap:
                        overlap_sentences.insert(0, prev_sentence)
                        overlap_tokens += prev_tokens
                    else:
                        break

                current_chunk = overlap_sentences + [sentence]
                current_tokens = overlap_tokens + sentence_tokens
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(chunk_text)

        return chunks

    async def _fallback_chunking(self, content: str) -> ChunkedContent:
        """Simple fallback chunking when smart methods fail."""
        try:
            token_chunks = self.split_by_tokens(content, self.chunk_size, self.chunk_overlap)

            chunks = []
            for i, chunk_text in enumerate(token_chunks):
                chunk = self.create_chunk(
                    content=chunk_text,
                    chunk_index=i,
                    chunk_type="fallback_token",
                    source_metadata={'splitting_method': 'fallback_token'}
                )
                chunks.append(chunk)

            metadata = self.create_base_metadata(content, {
                'chunking_method': 'fallback',
                'total_chunks': len(chunks)
            })

            return ChunkedContent(chunks, metadata)

        except Exception as e:
            logger.error(f"Even fallback chunking failed: {e}")
            # Last resort: return entire content as single chunk
            chunk = self.create_chunk(
                content=content,
                chunk_index=0,
                chunk_type="single_chunk",
                source_metadata={'splitting_method': 'none_failed'}
            )

            metadata = self.create_base_metadata(content, {
                'chunking_method': 'single_chunk',
                'total_chunks': 1,
                'error': str(e)
            })

            return ChunkedContent([chunk], metadata)
