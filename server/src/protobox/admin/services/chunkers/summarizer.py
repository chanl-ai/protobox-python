"""Summarizer that extracts key points and removes filler content."""

import json
import logging
from typing import Any

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from protobox.admin.config import settings

from .base_chunker import BaseChunker, ChunkedContent

logger = logging.getLogger(__name__)


class Summarizer(BaseChunker):
    """Summarizer that keeps only key points and removes filler content."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50, **kwargs):
        super().__init__(chunk_size, chunk_overlap)

        self.openai_client = None
        self.model = settings.openai_model
        self.compression_ratio = kwargs.get('compression_ratio', 0.6)  # Target 60% of original length
        self.preserve_structure = kwargs.get('preserve_structure', True)
        self.extract_bullet_points = kwargs.get('extract_bullet_points', True)

        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI not available, summarization will use rule-based fallback")
        elif not settings.openai_api_key:
            logger.warning("OpenAI API key not configured, summarization will use rule-based fallback")
        else:
            self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info(f"Summarizer initialized with OpenAI model: {self.model}")

    async def chunk(self, content: str, **kwargs) -> ChunkedContent:
        """
        Create summarized chunks with key points extracted.
        
        Args:
            content: Content to process
            **kwargs: Additional options
            
        Returns:
            ChunkedContent with summarized chunks
        """
        if not content.strip():
            return ChunkedContent([], self.create_base_metadata(content))

        try:
            # First split content into logical sections
            sections = await self._split_into_sections(content)

            # Summarize each section
            summarized_chunks = []

            for i, section in enumerate(sections):
                if self.openai_client:
                    summary_data = await self._summarize_with_openai(section, i)
                else:
                    summary_data = await self._summarize_fallback(section, i)

                # Create chunk from summary
                chunk = self.create_chunk(
                    content=summary_data['summary'],
                    chunk_index=i,
                    chunk_type="summarized",
                    source_metadata={
                        'original_length': len(section),
                        'summary_length': len(summary_data['summary']),
                        'compression_ratio': len(summary_data['summary']) / len(section) if len(section) > 0 else 0,
                        'key_points': summary_data.get('key_points', []),
                        'important_entities': summary_data.get('entities', []),
                        'summarization_method': summary_data.get('method', 'unknown')
                    }
                )

                summarized_chunks.append(chunk)

            # Calculate quality scores
            for chunk in summarized_chunks:
                chunk['quality_score'] = self._calculate_summary_quality_score(chunk)

            # Calculate overall statistics
            original_total_length = sum(len(section) for section in sections)
            summary_total_length = sum(len(chunk['content']) for chunk in summarized_chunks)
            actual_compression = summary_total_length / original_total_length if original_total_length > 0 else 0

            metadata = self.create_base_metadata(content, {
                'chunking_method': 'summarized',
                'total_chunks': len(summarized_chunks),
                'total_sections': len(sections),
                'openai_available': self.openai_client is not None,
                'target_compression_ratio': self.compression_ratio,
                'actual_compression_ratio': actual_compression,
                'original_total_length': original_total_length,
                'summary_total_length': summary_total_length,
                'average_quality_score': sum(
                    chunk['quality_score'] for chunk in summarized_chunks
                ) / len(summarized_chunks) if summarized_chunks else 0
            })

            logger.info(f"Summarization created {len(summarized_chunks)} chunks with {actual_compression:.2%} compression")

            return ChunkedContent(summarized_chunks, metadata)

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return await self._fallback_summarization(content)

    async def _split_into_sections(self, content: str) -> list[str]:
        """Split content into logical sections for summarization."""
        # Split by markdown headings first
        import re
        heading_pattern = r'^#{1,6}\s+.+$'
        lines = content.split('\n')

        sections = []
        current_section = []

        for line in lines:
            if re.match(heading_pattern, line.strip()) and current_section:
                sections.append('\n'.join(current_section).strip())
                current_section = [line]
            else:
                current_section.append(line)

        if current_section:
            sections.append('\n'.join(current_section).strip())

        # If no headings, split by paragraphs and group by token size
        if len(sections) <= 1:
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

            sections = []
            current_section = []
            current_tokens = 0
            target_section_size = self.chunk_size * 2  # Larger sections for better summarization

            for paragraph in paragraphs:
                para_tokens = self.count_tokens(paragraph)

                if current_tokens + para_tokens > target_section_size and current_section:
                    sections.append('\n\n'.join(current_section))
                    current_section = [paragraph]
                    current_tokens = para_tokens
                else:
                    current_section.append(paragraph)
                    current_tokens += para_tokens

            if current_section:
                sections.append('\n\n'.join(current_section))

        return [section for section in sections if len(section.strip()) > 100]  # Filter very short sections

    async def _summarize_with_openai(self, section: str, section_index: int) -> dict[str, Any]:
        """Summarize section using OpenAI."""
        try:
            prompt = self._create_summary_prompt(section)

            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting key information from text. Create concise summaries that preserve essential information while removing redundancy and filler content."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=min(1500, int(self.count_tokens(section) * self.compression_ratio * 1.5))
            )

            summary_text = response.choices[0].message.content
            return await self._parse_openai_summary_response(summary_text, section, section_index)

        except Exception as e:
            logger.warning(f"OpenAI summarization failed for section {section_index}: {e}")
            return await self._summarize_fallback(section, section_index)

    def _create_summary_prompt(self, section: str) -> str:
        """Create a prompt for OpenAI summarization."""
        target_length = int(len(section) * self.compression_ratio)

        prompt_parts = [
            "Summarize the following text, focusing on key information and removing filler content.",
            f"Target length: approximately {target_length} characters ({self.compression_ratio:.0%} of original).",
        ]

        if self.preserve_structure:
            prompt_parts.append("Preserve the overall structure and organization of the content.")

        if self.extract_bullet_points:
            prompt_parts.append("Format key points as bullet points when appropriate.")

        prompt_parts.extend([
            "",
            "Format your response as JSON:",
            "{",
            '  "summary": "Your concise summary here",',
            '  "key_points": ["point1", "point2", "point3"],',
            '  "entities": ["important entities or concepts"]',
            "}",
            "",
            f"Text to summarize:\n{section}"
        ])

        return '\n'.join(prompt_parts)

    async def _parse_openai_summary_response(self, summary_text: str, original_section: str, section_index: int) -> dict[str, Any]:
        """Parse OpenAI summary response."""
        try:
            summary_data = json.loads(summary_text.strip())

            return {
                'summary': summary_data.get('summary', ''),
                'key_points': summary_data.get('key_points', []),
                'entities': summary_data.get('entities', []),
                'method': 'openai'
            }

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse OpenAI summary JSON for section {section_index}")
            # Try to extract summary from text
            lines = summary_text.split('\n')
            summary = ''

            for line in lines:
                line = line.strip()
                if line and not line.startswith('{') and not line.startswith('}') and not line.startswith('"'):
                    if not summary:
                        summary = line
                    else:
                        summary += ' ' + line

            return {
                'summary': summary or await self._summarize_fallback(original_section, section_index)['summary'],
                'key_points': [],
                'entities': [],
                'method': 'openai_parsed'
            }

    async def _summarize_fallback(self, section: str, section_index: int) -> dict[str, Any]:
        """Summarize using rule-based approach."""
        # Extract sentences and rank by importance
        sentences = self.split_by_sentences(section)

        if not sentences:
            return {
                'summary': section,
                'key_points': [],
                'entities': [],
                'method': 'fallback_passthrough'
            }

        # Score sentences by importance
        sentence_scores = []

        for sentence in sentences:
            score = await self._score_sentence_importance(sentence, section)
            sentence_scores.append((sentence, score))

        # Sort by score and select top sentences
        sentence_scores.sort(key=lambda x: x[1], reverse=True)

        # Select sentences to meet compression ratio
        target_length = int(len(section) * self.compression_ratio)
        selected_sentences = []
        current_length = 0

        for sentence, score in sentence_scores:
            if current_length + len(sentence) <= target_length:
                selected_sentences.append(sentence)
                current_length += len(sentence)
            elif not selected_sentences:  # At least include one sentence
                selected_sentences.append(sentence)
                break

        # Reorder sentences by original position
        original_positions = {}
        for i, sentence in enumerate(sentences):
            original_positions[sentence] = i

        selected_sentences.sort(key=lambda x: original_positions.get(x, 999))

        summary = ' '.join(selected_sentences)

        # Extract key points and entities
        key_points = await self._extract_key_points(selected_sentences)
        entities = await self._extract_entities(section)

        return {
            'summary': summary,
            'key_points': key_points,
            'entities': entities,
            'method': 'rule_based'
        }

    async def _score_sentence_importance(self, sentence: str, full_section: str) -> float:
        """Score a sentence's importance for summarization."""
        score = 0.0

        # Length score (prefer medium-length sentences)
        length = len(sentence.split())
        if 8 <= length <= 25:
            score += 0.3
        elif length < 5:
            score -= 0.2

        # Position score (first and last sentences often important)
        sentences = self.split_by_sentences(full_section)
        position = sentences.index(sentence) if sentence in sentences else -1

        if position == 0:  # First sentence
            score += 0.2
        elif position == len(sentences) - 1 or position < len(sentences) * 0.3:  # Last sentence
            score += 0.1

        # Keyword score (sentences with important keywords)
        important_keywords = self._get_important_keywords(full_section)
        sentence_lower = sentence.lower()

        for keyword in important_keywords:
            if keyword.lower() in sentence_lower:
                score += 0.1

        # Structure score (sentences that introduce or conclude)
        sentence_lower = sentence.lower()
        structure_indicators = [
            'in summary', 'to conclude', 'therefore', 'as a result', 'importantly',
            'first', 'second', 'finally', 'moreover', 'furthermore', 'however',
            'the main', 'key point', 'essential', 'crucial', 'significant'
        ]

        for indicator in structure_indicators:
            if indicator in sentence_lower:
                score += 0.15
                break

        # Avoid sentences that are mostly questions or exclamations
        if sentence.strip().endswith('?'):
            score -= 0.1

        return max(0.0, score)

    def _get_important_keywords(self, text: str) -> list[str]:
        """Extract important keywords from text."""
        import re
        from collections import Counter

        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())

        # Remove common words
        stop_words = {
            'this', 'that', 'with', 'have', 'from', 'they', 'know', 'want',
            'been', 'good', 'much', 'some', 'time', 'very', 'when', 'come',
            'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such',
            'take', 'than', 'them', 'well', 'were', 'will', 'would', 'there',
            'could', 'other', 'after', 'first', 'also', 'back', 'only', 'think'
        }

        filtered_words = [word for word in words if word not in stop_words]
        word_freq = Counter(filtered_words)

        return [word for word, count in word_freq.most_common(10) if count > 1]

    async def _extract_key_points(self, sentences: list[str]) -> list[str]:
        """Extract key points from selected sentences."""
        key_points = []

        for sentence in sentences:
            # Clean up sentence for key point
            sentence = sentence.strip()

            # Skip very short sentences
            if len(sentence) < 20:
                continue

            # Extract the core point (remove lead-in phrases)
            cleanup_patterns = [
                r'^(In addition|Furthermore|Moreover|However|Therefore|Thus|As a result),?\s*',
                r'^(It is important to note that|It should be noted that|Note that)\s*',
                r'^(This means that|This suggests that|This indicates that)\s*'
            ]

            cleaned_sentence = sentence
            for pattern in cleanup_patterns:
                import re
                cleaned_sentence = re.sub(pattern, '', cleaned_sentence, flags=re.IGNORECASE)

            key_points.append(cleaned_sentence.strip())

        return key_points[:5]  # Limit to 5 key points

    async def _extract_entities(self, text: str) -> list[str]:
        """Extract important entities/concepts from text."""
        import re

        # Simple entity extraction using patterns
        entities = set()

        # Capitalized phrases (potential proper nouns)
        capitalized_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        entities.update(capitalized_phrases)

        # Numbers with units
        numbers_with_units = re.findall(r'\b\d+(?:\.\d+)?\s*(?:percent|%|dollars?|\$|years?|months?|days?|hours?|minutes?|seconds?)\b', text, re.IGNORECASE)
        entities.update(numbers_with_units)

        # Technical terms (words ending in common suffixes)
        technical_terms = re.findall(r'\b\w+(?:tion|sion|ment|ness|ity|ism|ology|graphy)\b', text, re.IGNORECASE)
        entities.update(technical_terms)

        return list(entities)[:10]  # Limit to 10 entities

    def _calculate_summary_quality_score(self, chunk: dict[str, Any]) -> float:
        """Calculate quality score for summarized chunk."""
        base_score = self.calculate_chunk_quality_score(chunk['content'])

        metadata = chunk.get('source_metadata', {})
        compression_ratio = metadata.get('compression_ratio', 1.0)
        key_points = metadata.get('key_points', [])

        # Bonus for good compression ratio
        if 0.3 <= compression_ratio <= 0.8:  # Good compression range
            base_score += 0.2
        elif compression_ratio < 0.3:  # Too compressed
            base_score -= 0.1
        elif compression_ratio > 0.9:  # Not compressed enough
            base_score -= 0.05

        # Bonus for extracted key points
        if key_points:
            base_score += 0.1 * min(len(key_points), 3) / 3

        # Bonus for OpenAI summarization
        if metadata.get('summarization_method') == 'openai':
            base_score += 0.15

        return min(1.0, base_score)

    async def _fallback_summarization(self, content: str) -> ChunkedContent:
        """Simple fallback when summarization fails."""
        try:
            # Just extract first sentence of each paragraph
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

            summary_sentences = []
            for paragraph in paragraphs:
                sentences = self.split_by_sentences(paragraph)
                if sentences:
                    summary_sentences.append(sentences[0])

            summary_text = ' '.join(summary_sentences)

            chunk = self.create_chunk(
                content=summary_text,
                chunk_index=0,
                chunk_type="fallback_summary",
                source_metadata={
                    'original_length': len(content),
                    'summary_length': len(summary_text),
                    'compression_ratio': len(summary_text) / len(content) if len(content) > 0 else 0,
                    'summarization_method': 'fallback'
                }
            )

            metadata = self.create_base_metadata(content, {
                'chunking_method': 'fallback_summary',
                'total_chunks': 1
            })

            return ChunkedContent([chunk], metadata)

        except Exception as e:
            logger.error(f"Even fallback summarization failed: {e}")
            return ChunkedContent([], self.create_base_metadata(content, {'error': str(e)}))
