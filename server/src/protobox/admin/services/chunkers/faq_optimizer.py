"""FAQ optimizer that generates Q&A pairs from content using OpenAI."""

import asyncio
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


class FAQOptimizer(BaseChunker):
    """FAQ optimizer that creates Q&A pairs from content sections."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50, **kwargs):
        super().__init__(chunk_size, chunk_overlap)

        self.openai_client = None
        self.model = settings.openai_model
        self.max_questions_per_section = kwargs.get('max_questions_per_section', 5)
        self.question_types = kwargs.get('question_types', [
            'what', 'how', 'why', 'when', 'where', 'who'
        ])

        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI not available, FAQ optimization will use rule-based fallback")
        elif not settings.openai_api_key:
            logger.warning("OpenAI API key not configured, FAQ optimization will use rule-based fallback")
        else:
            self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info(f"FAQ optimizer initialized with OpenAI model: {self.model}")

    async def chunk(self, content: str, **kwargs) -> ChunkedContent:
        """
        Create FAQ-optimized chunks with Q&A pairs.
        
        Args:
            content: Content to process
            **kwargs: Additional options
            
        Returns:
            ChunkedContent with Q&A pairs as chunks
        """
        if not content.strip():
            return ChunkedContent([], self.create_base_metadata(content))

        try:
            # First split content into logical sections
            sections = await self._split_into_sections(content)

            # Generate Q&A pairs for each section
            qa_chunks = []

            for i, section in enumerate(sections):
                if self.openai_client:
                    section_qas = await self._generate_qas_with_openai(section, i)
                else:
                    section_qas = await self._generate_qas_fallback(section, i)

                qa_chunks.extend(section_qas)

            # Calculate quality scores
            for chunk in qa_chunks:
                chunk['quality_score'] = self._calculate_qa_quality_score(chunk)

            metadata = self.create_base_metadata(content, {
                'chunking_method': 'faq_optimization',
                'total_chunks': len(qa_chunks),
                'total_sections': len(sections),
                'openai_available': self.openai_client is not None,
                'average_questions_per_section': len(qa_chunks) / len(sections) if sections else 0,
                'average_quality_score': sum(chunk['quality_score'] for chunk in qa_chunks) / len(qa_chunks) if qa_chunks else 0
            })

            logger.info(f"FAQ optimization created {len(qa_chunks)} Q&A pairs from {len(sections)} sections")

            return ChunkedContent(qa_chunks, metadata)

        except Exception as e:
            logger.error(f"FAQ optimization failed: {e}")
            # Fallback to basic rule-based Q&A generation
            return await self._fallback_faq_generation(content)

    async def _split_into_sections(self, content: str) -> list[str]:
        """Split content into logical sections for Q&A generation."""
        # Split by markdown headings
        import re
        heading_pattern = r'^#{1,6}\s+.+$'
        lines = content.split('\n')

        sections = []
        current_section = []

        for line in lines:
            if re.match(heading_pattern, line.strip()) and current_section:
                # Start new section at heading
                sections.append('\n'.join(current_section).strip())
                current_section = [line]
            else:
                current_section.append(line)

        # Add final section
        if current_section:
            sections.append('\n'.join(current_section).strip())

        # If no headings, split by paragraphs and group them
        if len(sections) <= 1:
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

            # Group paragraphs into sections of reasonable size
            sections = []
            current_section = []
            current_tokens = 0

            for paragraph in paragraphs:
                para_tokens = self.count_tokens(paragraph)

                if current_tokens + para_tokens > self.chunk_size and current_section:
                    sections.append('\n\n'.join(current_section))
                    current_section = [paragraph]
                    current_tokens = para_tokens
                else:
                    current_section.append(paragraph)
                    current_tokens += para_tokens

            if current_section:
                sections.append('\n\n'.join(current_section))

        return [section for section in sections if len(section.strip()) > 50]

    async def _generate_qas_with_openai(self, section: str, section_index: int) -> list[dict[str, Any]]:
        """Generate Q&A pairs using OpenAI."""
        try:
            prompt = self._create_qa_prompt(section)

            # Add timeout protection for OpenAI API call
            response = await asyncio.wait_for(
                self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert at creating clear, useful FAQ entries from text content. Generate questions that users would realistically ask about the content."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,
                    max_tokens=1500
                ),
                timeout=30.0  # 30 second timeout for OpenAI API calls
            )

            qa_text = response.choices[0].message.content
            return await self._parse_openai_qa_response(qa_text, section, section_index)

        except TimeoutError:
            logger.warning(f"OpenAI Q&A generation timed out for section {section_index}, using fallback")
            return await self._generate_qas_fallback(section, section_index)
        except Exception as e:
            logger.warning(f"OpenAI Q&A generation failed for section {section_index}: {e}")
            return await self._generate_qas_fallback(section, section_index)

    def _create_qa_prompt(self, section: str) -> str:
        """Create a prompt for OpenAI Q&A generation."""
        return f"""
Generate {self.max_questions_per_section} clear, specific questions and answers based on the following content. 
The questions should be what users would naturally ask about this topic.

Format your response as JSON with this structure:
{{
  "qa_pairs": [
    {{
      "question": "What is...",
      "answer": "...",
      "keywords": ["keyword1", "keyword2"],
      "question_type": "what"
    }}
  ]
}}

Content:
{section}

Guidelines:
- Questions should be diverse (what, how, why, when, where)
- Answers should be complete but concise
- Include relevant keywords for each Q&A pair
- Focus on the most important information in the content
"""

    async def _parse_openai_qa_response(self, qa_text: str, section: str, section_index: int) -> list[dict[str, Any]]:
        """Parse OpenAI response into Q&A chunks."""
        try:
            # Try to parse JSON response
            qa_data = json.loads(qa_text.strip())
            qa_pairs = qa_data.get('qa_pairs', [])

            chunks = []
            for i, qa_pair in enumerate(qa_pairs):
                question = qa_pair.get('question', '').strip()
                answer = qa_pair.get('answer', '').strip()

                if question and answer:
                    chunk = self.create_chunk(
                        content=f"Q: {question}\n\nA: {answer}",
                        chunk_index=len(chunks),
                        chunk_type="faq_pair",
                        source_metadata={
                            'section_index': section_index,
                            'qa_index': i,
                            'question': question,
                            'answer': answer,
                            'keywords': qa_pair.get('keywords', []),
                            'question_type': qa_pair.get('question_type', 'unknown'),
                            'generation_method': 'openai'
                        }
                    )
                    chunks.append(chunk)

            return chunks

        except json.JSONDecodeError:
            logger.warning("Failed to parse OpenAI JSON response, using text parsing")
            return await self._parse_text_qa_response(qa_text, section, section_index)

    async def _parse_text_qa_response(self, qa_text: str, section: str, section_index: int) -> list[dict[str, Any]]:
        """Parse non-JSON Q&A response."""
        chunks = []

        # Split by Q: or Question: patterns
        import re
        qa_pattern = r'Q(?:uestion)?:\s*(.+?)\n+A(?:nswer)?:\s*(.+?)(?=\n+Q(?:uestion)?:|\n+$|$)'
        matches = re.findall(qa_pattern, qa_text, re.DOTALL | re.IGNORECASE)

        for i, (question, answer) in enumerate(matches):
            question = question.strip()
            answer = answer.strip()

            if question and answer:
                chunk = self.create_chunk(
                    content=f"Q: {question}\n\nA: {answer}",
                    chunk_index=len(chunks),
                    chunk_type="faq_pair",
                    source_metadata={
                        'section_index': section_index,
                        'qa_index': i,
                        'question': question,
                        'answer': answer,
                        'generation_method': 'openai_text_parsed'
                    }
                )
                chunks.append(chunk)

        return chunks

    async def _generate_qas_fallback(self, section: str, section_index: int) -> list[dict[str, Any]]:
        """Generate Q&A pairs using rule-based approach."""
        chunks = []

        # Extract key sentences that could be answers
        sentences = self.split_by_sentences(section)

        # Generate questions for informative sentences
        for i, sentence in enumerate(sentences[:self.max_questions_per_section]):
            if len(sentence.strip()) < 20:  # Skip very short sentences
                continue

            # Generate simple questions based on sentence content
            questions = self._generate_questions_for_sentence(sentence)

            for j, question in enumerate(questions):
                if question:
                    chunk = self.create_chunk(
                        content=f"Q: {question}\n\nA: {sentence}",
                        chunk_index=len(chunks),
                        chunk_type="faq_pair",
                        source_metadata={
                            'section_index': section_index,
                            'qa_index': len(chunks),
                            'sentence_index': i,
                            'question': question,
                            'answer': sentence,
                            'generation_method': 'rule_based'
                        }
                    )
                    chunks.append(chunk)
                    break  # One question per sentence for fallback

        return chunks

    def _generate_questions_for_sentence(self, sentence: str) -> list[str]:
        """Generate simple questions for a sentence using rules."""
        sentence = sentence.strip()
        questions = []

        # Simple question generation based on sentence patterns
        lower_sentence = sentence.lower()

        # What questions
        if any(word in lower_sentence for word in ['is', 'are', 'means', 'refers to']):
            # Extract the subject
            words = sentence.split()
            if len(words) > 2:
                questions.append(f"What {' '.join(words[1:3])}?")

        # How questions
        if any(word in lower_sentence for word in ['process', 'method', 'way', 'steps']):
            questions.append("How does this work?")

        # Why questions
        if any(word in lower_sentence for word in ['because', 'reason', 'purpose']):
            questions.append("Why is this important?")

        # When questions
        if any(word in lower_sentence for word in ['when', 'time', 'date', 'during']):
            questions.append("When does this happen?")

        # Generic fallback
        if not questions:
            # Extract first few words as topic
            words = sentence.split()[:4]
            topic = ' '.join(words)
            questions.append(f"What about {topic}?")

        return questions[:1]  # Return only the first question

    def _calculate_qa_quality_score(self, chunk: dict[str, Any]) -> float:
        """Calculate quality score for Q&A chunk."""
        base_score = self.calculate_chunk_quality_score(chunk['content'])

        metadata = chunk.get('source_metadata', {})
        question = metadata.get('question', '')
        answer = metadata.get('answer', '')

        # Bonus for well-formed questions
        if question and question.strip().endswith('?'):
            base_score += 0.1

        # Bonus for complete answers
        if answer and len(answer.strip()) > 20:
            base_score += 0.1

        # Bonus for OpenAI generation
        if metadata.get('generation_method') == 'openai':
            base_score += 0.2

        # Penalty for very short Q&A pairs
        total_length = len(question) + len(answer)
        if total_length < 50:
            base_score *= 0.7

        return min(1.0, base_score)

    async def _fallback_faq_generation(self, content: str) -> ChunkedContent:
        """Simple fallback when all else fails."""
        try:
            # Split content into paragraphs and create simple Q&A
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

            chunks = []
            for i, paragraph in enumerate(paragraphs[:10]):  # Limit to 10 paragraphs
                if len(paragraph) > 30:
                    question = f"What is discussed in section {i + 1}?"
                    chunk = self.create_chunk(
                        content=f"Q: {question}\n\nA: {paragraph}",
                        chunk_index=i,
                        chunk_type="faq_pair",
                        source_metadata={
                            'question': question,
                            'answer': paragraph,
                            'generation_method': 'fallback'
                        }
                    )
                    chunks.append(chunk)

            metadata = self.create_base_metadata(content, {
                'chunking_method': 'faq_fallback',
                'total_chunks': len(chunks)
            })

            return ChunkedContent(chunks, metadata)

        except Exception as e:
            logger.error(f"Even fallback FAQ generation failed: {e}")
            return ChunkedContent([], self.create_base_metadata(content, {'error': str(e)}))
