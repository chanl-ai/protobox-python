"""Topic headerizer that adds section summaries at the start of chunks."""

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


class TopicHeaderizer(BaseChunker):
    """Chunker that adds brief topic summaries at the start of each section."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50, **kwargs):
        super().__init__(chunk_size, chunk_overlap)

        self.openai_client = None
        self.model = settings.openai_model
        self.header_max_length = kwargs.get('header_max_length', 100)
        self.include_keywords = kwargs.get('include_keywords', True)

        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI not available, topic headers will use rule-based fallback")
        elif not settings.openai_api_key:
            logger.warning("OpenAI API key not configured, topic headers will use rule-based fallback")
        else:
            self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info(f"Topic headerizer initialized with OpenAI model: {self.model}")

    async def chunk(self, content: str, **kwargs) -> ChunkedContent:
        """
        Create chunks with topic headers for better context.
        
        Args:
            content: Content to process
            **kwargs: Additional options
            
        Returns:
            ChunkedContent with topic headers added to chunks
        """
        if not content.strip():
            return ChunkedContent([], self.create_base_metadata(content))

        try:
            # First create base chunks using smart splitting
            base_chunks = await self._create_base_chunks(content)

            # Add topic headers to each chunk
            headerized_chunks = []

            for i, chunk_text in enumerate(base_chunks):
                if self.openai_client:
                    header = await self._generate_header_with_openai(chunk_text, i)
                else:
                    header = await self._generate_header_fallback(chunk_text, i)

                # Combine header with chunk content
                headerized_content = await self._combine_header_and_content(header, chunk_text)

                chunk = self.create_chunk(
                    content=headerized_content,
                    chunk_index=i,
                    chunk_type="topic_headerized",
                    source_metadata={
                        'topic_header': header.get('summary', ''),
                        'keywords': header.get('keywords', []),
                        'original_chunk_length': len(chunk_text),
                        'header_generation_method': header.get('method', 'unknown')
                    }
                )

                headerized_chunks.append(chunk)

            # Calculate quality scores
            for chunk in headerized_chunks:
                chunk['quality_score'] = self._calculate_headerized_quality_score(chunk)

            metadata = self.create_base_metadata(content, {
                'chunking_method': 'topic_headerized',
                'total_chunks': len(headerized_chunks),
                'openai_available': self.openai_client is not None,
                'average_header_length': sum(
                    len(chunk['source_metadata']['topic_header'])
                    for chunk in headerized_chunks
                ) / len(headerized_chunks) if headerized_chunks else 0,
                'average_quality_score': sum(
                    chunk['quality_score'] for chunk in headerized_chunks
                ) / len(headerized_chunks) if headerized_chunks else 0
            })

            logger.info(f"Topic headerization created {len(headerized_chunks)} chunks with headers")

            return ChunkedContent(headerized_chunks, metadata)

        except Exception as e:
            logger.error(f"Topic headerization failed: {e}")
            return await self._fallback_headerization(content)

    async def _create_base_chunks(self, content: str) -> list[str]:
        """Create base chunks using smart splitting."""
        # Split by structural elements first
        chunks = []

        # Split by markdown headings
        import re
        heading_pattern = r'^#{1,6}\s+.+$'
        lines = content.split('\n')

        current_section = []
        for line in lines:
            if re.match(heading_pattern, line.strip()) and current_section:
                # End current section
                section_text = '\n'.join(current_section).strip()
                if section_text:
                    chunks.extend(await self._split_section_by_size(section_text))
                current_section = [line]
            else:
                current_section.append(line)

        # Add final section
        if current_section:
            section_text = '\n'.join(current_section).strip()
            if section_text:
                chunks.extend(await self._split_section_by_size(section_text))

        # If no headings found, split by paragraphs
        if not chunks:
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            for paragraph in paragraphs:
                chunks.extend(await self._split_section_by_size(paragraph))

        return chunks

    async def _split_section_by_size(self, section: str) -> list[str]:
        """Split a section into appropriately sized chunks."""
        token_count = self.count_tokens(section)

        if token_count <= self.chunk_size:
            return [section]

        # Split by sentences first
        sentences = self.split_by_sentences(section)

        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_tokens = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    async def _generate_header_with_openai(self, chunk_text: str, chunk_index: int) -> dict[str, Any]:
        """Generate topic header using OpenAI."""
        try:
            prompt = self._create_header_prompt(chunk_text)

            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at creating concise, informative section summaries. Create brief headers that help readers understand what a text section covers."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=200
            )

            header_text = response.choices[0].message.content
            return await self._parse_openai_header_response(header_text, chunk_index)

        except Exception as e:
            logger.warning(f"OpenAI header generation failed for chunk {chunk_index}: {e}")
            return await self._generate_header_fallback(chunk_text, chunk_index)

    def _create_header_prompt(self, chunk_text: str) -> str:
        """Create a prompt for OpenAI header generation."""
        return f"""
Create a brief, informative header summary for the following text section. The header should:
1. Be {self.header_max_length} characters or less
2. Capture the main topic/theme
3. Include 2-3 relevant keywords

Format your response as JSON:
{{
  "summary": "Brief topic summary here",
  "keywords": ["keyword1", "keyword2", "keyword3"]
}}

Text section:
{chunk_text[:1000]}...
"""

    async def _parse_openai_header_response(self, header_text: str, chunk_index: int) -> dict[str, Any]:
        """Parse OpenAI header response."""
        try:
            header_data = json.loads(header_text.strip())

            return {
                'summary': header_data.get('summary', '')[:self.header_max_length],
                'keywords': header_data.get('keywords', [])[:5],  # Limit to 5 keywords
                'method': 'openai'
            }

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse OpenAI header JSON for chunk {chunk_index}")
            # Try to extract summary from text
            lines = header_text.split('\n')
            summary = ''
            for line in lines:
                line = line.strip()
                if line and not line.startswith('{') and not line.startswith('}'):
                    summary = line[:self.header_max_length]
                    break

            return {
                'summary': summary or 'Content Summary',
                'keywords': [],
                'method': 'openai_parsed'
            }

    async def _generate_header_fallback(self, chunk_text: str, chunk_index: int) -> dict[str, Any]:
        """Generate header using rule-based approach."""
        # Extract first sentence as potential summary
        sentences = self.split_by_sentences(chunk_text)

        if sentences:
            first_sentence = sentences[0].strip()

            # If first sentence is very long, truncate it
            if len(first_sentence) > self.header_max_length:
                words = first_sentence.split()
                summary = ''
                for word in words:
                    if len(summary + ' ' + word) <= self.header_max_length - 3:
                        summary += (' ' + word) if summary else word
                    else:
                        summary += '...'
                        break
            else:
                summary = first_sentence
        else:
            summary = f"Section {chunk_index + 1}"

        # Extract keywords using simple frequency analysis
        keywords = self._extract_keywords_simple(chunk_text)

        return {
            'summary': summary,
            'keywords': keywords,
            'method': 'rule_based'
        }

    def _extract_keywords_simple(self, text: str) -> list[str]:
        """Extract keywords using simple word frequency."""
        import re
        from collections import Counter

        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

        # Remove common stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
            'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his',
            'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy',
            'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'this', 'that',
            'with', 'have', 'from', 'they', 'know', 'want', 'been', 'good', 'much',
            'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long',
            'make', 'many', 'over', 'such', 'take', 'than', 'them', 'well', 'were'
        }

        filtered_words = [word for word in words if word not in stop_words and len(word) > 3]

        # Get most common words
        word_freq = Counter(filtered_words)
        return [word for word, count in word_freq.most_common(5)]

    async def _combine_header_and_content(self, header: dict[str, Any], content: str) -> str:
        """Combine header summary with original content."""
        summary = header.get('summary', '').strip()
        keywords = header.get('keywords', [])

        if not summary:
            return content

        # Create header section
        header_parts = [f"## {summary}"]

        if self.include_keywords and keywords:
            keywords_text = ', '.join(keywords[:3])  # Limit to 3 keywords for brevity
            header_parts.append(f"*Keywords: {keywords_text}*")

        header_section = '\n'.join(header_parts)

        # Combine with content
        return f"{header_section}\n\n{content}"

    def _calculate_headerized_quality_score(self, chunk: dict[str, Any]) -> float:
        """Calculate quality score for headerized chunk."""
        base_score = self.calculate_chunk_quality_score(chunk['content'])

        metadata = chunk.get('source_metadata', {})
        header = metadata.get('topic_header', '')
        keywords = metadata.get('keywords', [])

        # Bonus for good headers
        if header and len(header.strip()) > 10:
            base_score += 0.1

        # Bonus for keywords
        if keywords:
            base_score += 0.05 * min(len(keywords), 3)

        # Bonus for OpenAI generation
        if metadata.get('header_generation_method') == 'openai':
            base_score += 0.1

        # Ensure header isn't too long relative to content
        original_length = metadata.get('original_chunk_length', len(chunk['content']))
        if header and len(header) < original_length * 0.3:  # Header should be < 30% of content
            base_score += 0.05

        return min(1.0, base_score)

    async def _fallback_headerization(self, content: str) -> ChunkedContent:
        """Simple fallback when headerization fails."""
        try:
            # Just split content into chunks without headers
            token_chunks = self.split_by_tokens(content, self.chunk_size, self.chunk_overlap)

            chunks = []
            for i, chunk_text in enumerate(token_chunks):
                # Add simple header
                header = f"Section {i + 1}"
                headerized_content = f"## {header}\n\n{chunk_text}"

                chunk = self.create_chunk(
                    content=headerized_content,
                    chunk_index=i,
                    chunk_type="simple_headerized",
                    source_metadata={
                        'topic_header': header,
                        'keywords': [],
                        'header_generation_method': 'fallback'
                    }
                )
                chunks.append(chunk)

            metadata = self.create_base_metadata(content, {
                'chunking_method': 'fallback_headerized',
                'total_chunks': len(chunks)
            })

            return ChunkedContent(chunks, metadata)

        except Exception as e:
            logger.error(f"Even fallback headerization failed: {e}")
            return ChunkedContent([], self.create_base_metadata(content, {'error': str(e)}))
