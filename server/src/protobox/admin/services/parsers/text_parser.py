"""Enhanced text parser for plain text and markdown files with comprehensive logging."""

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .base_parser import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)


class TextParser(BaseParser):
    """Parser for plain text and markdown files."""

    def __init__(self):
        super().__init__()
        self.supported_extensions = {'.txt', '.md', '.markdown', '.rst', '.csv'}

    async def parse(self, file_path: str, detect_structure: bool = True, **kwargs) -> ParsedDocument:
        """
        Parse text document with comprehensive logging and standardized output.
        
        Args:
            file_path: Path to text file
            detect_structure: Whether to detect and preserve text structure
            **kwargs: Additional parsing options
            
        Returns:
            ParsedDocument with extracted content and metadata
        """
        start_time = datetime.now(UTC)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Text file not found: {file_path}")

        filename = Path(file_path).name
        file_size = os.path.getsize(file_path)
        file_ext = Path(file_path).suffix.lower()

        logger.info(f"🔍 Starting text parsing for {filename} ({file_size:,} bytes, {file_ext})")

        try:
            # Read file content
            logger.debug(f"📖 Reading file content from {file_path}")
            with open(file_path, encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if not content.strip():
                raise ValueError("File is empty or contains no readable content")

            logger.info(f"📝 File read successfully: {len(content):,} characters")

            # Process based on file type with timeout protection
            logger.debug(f"🔧 Processing {file_ext} content with structure detection: {detect_structure}")

            try:
                if file_ext == '.csv':
                    processed_content, text_metadata = await self._run_with_timeout(
                        self._process_csv_content(content)
                    )
                    logger.info(f"📊 CSV processing complete: {text_metadata.get('rows', 0)} rows, {text_metadata.get('columns', 0)} columns")
                elif file_ext in ['.md', '.markdown']:
                    processed_content, text_metadata = await self._run_with_timeout(
                        self._process_markdown_content(content, detect_structure)
                    )
                    logger.info(f"📋 Markdown processing complete: {text_metadata.get('headings', [])} headings, {text_metadata.get('code_blocks', 0)} code blocks")
                elif file_ext == '.rst':
                    processed_content, text_metadata = await self._run_with_timeout(
                        self._process_rst_content(content, detect_structure)
                    )
                    logger.info(f"📚 RST processing complete: {text_metadata.get('headings', [])} headings, {text_metadata.get('directives', 0)} directives")
                else:
                    # Plain text
                    processed_content, text_metadata = await self._run_with_timeout(
                        self._process_plain_text(content, detect_structure)
                    )
                    logger.info(f"📄 Plain text processing complete: {text_metadata.get('paragraphs', 0)} paragraphs, {text_metadata.get('potential_headings', 0)} potential headings")

            except TimeoutError:
                logger.warning(f"⏰ Text processing timed out for {filename} after {self.processing_timeout}s")
                # Create partial results with basic content
                processed_content = content[:10000] + "\n\n[CONTENT TRUNCATED DUE TO TIMEOUT]"
                text_metadata = {
                    'processing_error': f"Processing timed out after {self.processing_timeout}s",
                    'processing_status': 'partial',
                    'content_truncated': True,
                    'original_length': len(content),
                    'processed_length': len(processed_content)
                }

            # Analyze text statistics with timeout protection
            logger.debug(f"📊 Analyzing text statistics for {filename}")
            try:
                text_stats = await self._run_with_timeout(
                    self._analyze_text_statistics(processed_content)
                )
            except TimeoutError:
                logger.warning(f"⏰ Text statistics analysis timed out for {filename}")
                text_stats = {
                    'character_count': len(processed_content),
                    'word_count': len(processed_content.split()),
                    'line_count': processed_content.count('\n'),
                    'processing_error': 'Statistics analysis timed out',
                    'processing_status': 'partial'
                }

            # Calculate processing time
            end_time = datetime.now(UTC)
            processing_time_seconds = (end_time - start_time).total_seconds()

            # Create comprehensive metadata
            metadata = self._create_base_metadata(filename, file_size)
            metadata.update({
                'source_type': 'text',
                'file_extension': file_ext,
                'text_metadata': text_metadata,
                'text_statistics': text_stats,
                'detect_structure': detect_structure,
                'content_type': self._get_content_type(file_ext),
                'processing_time_seconds': processing_time_seconds,
                'parser_version': '2.0.0',
                'extraction_timestamp': end_time.isoformat(),
                'warnings': [],
                'errors': []
            })

            # Check for timeout warnings
            if text_metadata.get('processing_status') == 'partial':
                metadata['warnings'].append("Text processing completed with timeout - using partial results")
                metadata['processing_status'] = 'partial'

            if text_stats.get('processing_status') == 'partial':
                metadata['warnings'].append("Statistics analysis completed with timeout - using partial results")

            # Enhanced completion logging
            logger.info(f"✅ Text parsing complete for {filename}: {processing_time_seconds:.2f}s")
            logger.info(f"📊 Content statistics: {text_stats['character_count']:,} chars, {text_stats['word_count']:,} words, {text_stats['line_count']:,} lines")

            # Log structure insights
            if detect_structure and text_metadata:
                structure_items = []
                if 'headings' in text_metadata and text_metadata['headings']:
                    structure_items.append(f"{len(text_metadata['headings'])} headings")
                if 'paragraphs' in text_metadata:
                    structure_items.append(f"{text_metadata['paragraphs']} paragraphs")
                if 'code_blocks' in text_metadata:
                    structure_items.append(f"{text_metadata['code_blocks']} code blocks")
                if 'tables' in text_metadata:
                    structure_items.append(f"{text_metadata['tables']} tables")

                if structure_items:
                    logger.info(f"🔧 Structure detected: {', '.join(structure_items)}")

            # Performance insights
            if processing_time_seconds > 1.0:
                logger.warning(f"🐌 Slow processing: {processing_time_seconds:.2f}s (consider optimizing)")
            else:
                logger.debug(f"⚡ Good performance: {processing_time_seconds:.2f}s")

            return ParsedDocument(processed_content, metadata)

        except Exception as e:
            logger.error(f"❌ Failed to parse text {filename}: {e}")
            raise

    async def _process_csv_content(self, content: str) -> tuple[str, dict[str, Any]]:
        """Process CSV content into readable format."""
        lines = content.strip().split('\n')

        if not lines:
            return content, {'type': 'csv', 'rows': 0}

        # Detect delimiter
        delimiters = [',', ';', '\t', '|']
        best_delimiter = ','
        max_columns = 0

        for delimiter in delimiters:
            columns = len(lines[0].split(delimiter))
            if columns > max_columns:
                max_columns = columns
                best_delimiter = delimiter

        # Parse CSV
        rows = []
        for line in lines:
            if line.strip():
                row = [cell.strip().strip('"').strip("'") for cell in line.split(best_delimiter)]
                rows.append(row)

        if not rows:
            return content, {'type': 'csv', 'rows': 0}

        # Convert to markdown table
        markdown_lines = []

        # Header
        if len(rows) > 1:
            headers = rows[0]
            markdown_lines.append('| ' + ' | '.join(headers) + ' |')
            markdown_lines.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')

            # Data rows
            for row in rows[1:]:
                # Ensure same number of columns
                while len(row) < len(headers):
                    row.append('')
                row = row[:len(headers)]

                # Escape pipe characters
                escaped_row = [cell.replace('|', '\\|') for cell in row]
                markdown_lines.append('| ' + ' | '.join(escaped_row) + ' |')
        else:
            # Single row
            row = rows[0]
            markdown_lines.append('| ' + ' | '.join(row) + ' |')

        processed_content = '\n'.join(markdown_lines)

        metadata = {
            'type': 'csv',
            'rows': len(rows),
            'columns': len(rows[0]) if rows else 0,
            'delimiter': best_delimiter,
            'has_header': len(rows) > 1
        }

        return processed_content, metadata

    async def _process_markdown_content(self, content: str, detect_structure: bool) -> tuple[str, dict[str, Any]]:
        """Process markdown content."""
        if not detect_structure:
            return content, {'type': 'markdown', 'structure_detected': False}

        lines = content.split('\n')
        structure_info = {
            'type': 'markdown',
            'headings': [],
            'code_blocks': 0,
            'links': 0,
            'images': 0,
            'tables': 0,
            'lists': 0
        }

        in_code_block = False
        current_list_level = 0

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Code blocks
            if stripped.startswith('```'):
                in_code_block = not in_code_block
                if in_code_block:
                    structure_info['code_blocks'] += 1

            if in_code_block:
                continue

            # Headings
            if stripped.startswith('#'):
                level = len(stripped) - len(stripped.lstrip('#'))
                heading_text = stripped.lstrip('#').strip()
                structure_info['headings'].append({
                    'level': level,
                    'text': heading_text,
                    'line': line_num
                })

            # Links
            structure_info['links'] += line.count('](')

            # Images
            structure_info['images'] += line.count('![')

            # Tables
            if '|' in stripped and stripped.count('|') >= 2:
                structure_info['tables'] += 1

            # Lists
            if stripped.startswith(('-', '*', '+')):
                structure_info['lists'] += 1

        return content, structure_info

    async def _process_rst_content(self, content: str, detect_structure: bool) -> tuple[str, dict[str, Any]]:
        """Process reStructuredText content."""
        if not detect_structure:
            return content, {'type': 'rst', 'structure_detected': False}

        lines = content.split('\n')
        structure_info = {
            'type': 'rst',
            'headings': [],
            'directives': 0,
            'references': 0
        }

        # Basic RST structure detection
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Headings (look for underline patterns)
            if line_num < len(lines) - 1:
                next_line = lines[line_num].strip()
                if next_line and all(c in '=-~`#"^' for c in next_line) and len(next_line) >= len(stripped):
                    structure_info['headings'].append({
                        'text': stripped,
                        'line': line_num,
                        'underline_char': next_line[0]
                    })

            # Directives
            if stripped.startswith('.. '):
                structure_info['directives'] += 1

            # References
            if '_' in stripped and '`' in stripped:
                structure_info['references'] += 1

        return content, structure_info

    async def _process_plain_text(self, content: str, detect_structure: bool) -> tuple[str, dict[str, Any]]:
        """Process plain text content."""
        if not detect_structure:
            return content, {'type': 'plain_text', 'structure_detected': False}

        lines = content.split('\n')
        structure_info = {
            'type': 'plain_text',
            'paragraphs': 0,
            'empty_lines': 0,
            'potential_headings': 0,
            'bullet_lists': 0,
            'numbered_lists': 0
        }

        current_paragraph_lines = 0

        for line in lines:
            stripped = line.strip()

            if not stripped:
                structure_info['empty_lines'] += 1
                if current_paragraph_lines > 0:
                    structure_info['paragraphs'] += 1
                    current_paragraph_lines = 0
            else:
                current_paragraph_lines += 1

                # Potential headings (short lines that could be titles)
                if len(stripped) < 60 and not stripped.endswith(('.', '!', '?', ':')):
                    structure_info['potential_headings'] += 1

                # Lists
                if stripped.startswith(('-', '*', '•')):
                    structure_info['bullet_lists'] += 1
                elif stripped[:3].replace('.', '').replace(')', '').isdigit():
                    structure_info['numbered_lists'] += 1

        # Add final paragraph if exists
        if current_paragraph_lines > 0:
            structure_info['paragraphs'] += 1

        return content, structure_info

    async def _analyze_text_statistics(self, content: str) -> dict[str, Any]:
        """Analyze basic text statistics."""
        import re

        stats = {
            'character_count': len(content),
            'character_count_no_spaces': len(content.replace(' ', '')),
            'word_count': len(content.split()),
            'line_count': len(content.split('\n')),
            'paragraph_count': len([p for p in content.split('\n\n') if p.strip()]),
            'sentence_count': len(re.findall(r'[.!?]+', content)),
            'average_word_length': 0,
            'average_sentence_length': 0
        }

        words = content.split()
        if words:
            stats['average_word_length'] = sum(len(word) for word in words) / len(words)

        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            sentence_word_counts = [len(sentence.split()) for sentence in sentences]
            stats['average_sentence_length'] = sum(sentence_word_counts) / len(sentence_word_counts)

        return stats

    def _get_content_type(self, file_ext: str) -> str:
        """Get content type based on file extension."""
        content_types = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.markdown': 'text/markdown',
            '.rst': 'text/x-rst',
            '.csv': 'text/csv'
        }
        return content_types.get(file_ext, 'text/plain')

    async def parse_bytes(self, file_bytes: bytes, filename: str, **kwargs) -> ParsedDocument:
        """Parse text from bytes."""
        try:
            content = file_bytes.decode('utf-8', errors='ignore')
            file_ext = Path(filename).suffix.lower()

            detect_structure = kwargs.get('detect_structure', True)

            # Process based on file type
            if file_ext == '.csv':
                processed_content, text_metadata = await self._process_csv_content(content)
            elif file_ext in ['.md', '.markdown']:
                processed_content, text_metadata = await self._process_markdown_content(content, detect_structure)
            elif file_ext == '.rst':
                processed_content, text_metadata = await self._process_rst_content(content, detect_structure)
            else:
                processed_content, text_metadata = await self._process_plain_text(content, detect_structure)

            # Analyze statistics
            text_stats = await self._analyze_text_statistics(processed_content)

            # Create metadata
            metadata = self._create_base_metadata(filename, len(file_bytes))
            metadata.update({
                'text_metadata': text_metadata,
                'text_statistics': text_stats,
                'detect_structure': detect_structure,
                'content_type': self._get_content_type(file_ext)
            })

            return ParsedDocument(processed_content, metadata)

        except Exception as e:
            logger.error(f"Failed to parse text from bytes: {e}")
            raise

    async def parse_text(self, text_content: str, title: str = "Text Content", **kwargs) -> ParsedDocument:
        """
        Parse raw text content with comprehensive logging and standardized output.
        
        Args:
            text_content: Raw text content to parse
            title: Title for the content
            **kwargs: Additional parsing options
            
        Returns:
            ParsedDocument with processed content and metadata
        """
        start_time = datetime.now(UTC)

        if not text_content.strip():
            raise ValueError("Text content cannot be empty")

        logger.info(f"🔍 Starting raw text parsing for '{title}' ({len(text_content):,} characters)")

        try:
            # Clean and structure the content
            logger.debug("🧹 Cleaning and structuring text content")
            content = self._clean_text_content(text_content)

            # Analyze text statistics with timeout protection
            logger.debug("📊 Analyzing text statistics")
            try:
                text_stats = await self._run_with_timeout(
                    self._analyze_text_statistics(content)
                )
            except TimeoutError:
                logger.warning(f"⏰ Text statistics analysis timed out for '{title}'")
                text_stats = {
                    'character_count': len(content),
                    'word_count': len(content.split()),
                    'line_count': content.count('\n'),
                    'processing_error': 'Statistics analysis timed out',
                    'processing_status': 'partial'
                }

            # Detect language and structure with timeout protection
            logger.debug("🔍 Detecting language and structure")
            try:
                language = await self._run_with_timeout(
                    self._detect_language_async(text_content)
                )
            except TimeoutError:
                logger.warning(f"⏰ Language detection timed out for '{title}'")
                language = 'unknown'

            try:
                structure_info = await self._run_with_timeout(
                    self._detect_text_structure_async(text_content)
                )
            except TimeoutError:
                logger.warning(f"⏰ Structure detection timed out for '{title}'")
                structure_info = {
                    'paragraphs': content.count('\n\n'),
                    'potential_headings': 0,
                    'processing_error': 'Structure detection timed out',
                    'processing_status': 'partial'
                }

            # Calculate processing time
            end_time = datetime.now(UTC)
            processing_time_seconds = (end_time - start_time).total_seconds()

            # Create comprehensive metadata
            metadata = self._create_base_metadata(f"{title}.txt", len(text_content.encode('utf-8')))
            metadata.update({
                'source_type': 'raw_text',
                'title': title,
                'content_type': 'raw_text',
                'character_count': len(text_content),
                'line_count': len(text_content.split('\n')),
                'word_count': len(text_content.split()),
                'language': language,
                'structure_detected': structure_info,
                'text_statistics': text_stats,
                'processing_time_seconds': processing_time_seconds,
                'parser_version': '2.0.0',
                'extraction_timestamp': end_time.isoformat(),
                'warnings': [],
                'errors': []
            })

            # Check for timeout warnings
            if text_stats.get('processing_status') == 'partial':
                metadata['warnings'].append("Text statistics analysis completed with timeout - using partial results")
                metadata['processing_status'] = 'partial'

            if structure_info.get('processing_status') == 'partial':
                metadata['warnings'].append("Structure detection completed with timeout - using partial results")
                if metadata.get('processing_status') != 'partial':
                    metadata['processing_status'] = 'partial'

            # Enhanced completion logging
            logger.info(f"✅ Raw text parsing complete for '{title}': {processing_time_seconds:.2f}s")
            logger.info(f"📊 Content statistics: {text_stats['character_count']:,} chars, {text_stats['word_count']:,} words, {text_stats['line_count']:,} lines")

            # Log language and structure insights
            if language != 'unknown':
                logger.info(f"🌍 Language detected: {language}")

            if structure_info:
                structure_items = []
                if structure_info.get('paragraphs'):
                    structure_items.append(f"{structure_info['paragraphs']} paragraphs")
                if structure_info.get('potential_headings'):
                    structure_items.append(f"{structure_info['potential_headings']} potential headings")
                if structure_info.get('bullet_lists'):
                    structure_items.append(f"{structure_info['bullet_lists']} bullet lists")
                if structure_info.get('numbered_lists'):
                    structure_items.append(f"{structure_info['numbered_lists']} numbered lists")

                if structure_items:
                    logger.info(f"🔧 Structure detected: {', '.join(structure_items)}")

            # Performance insights
            if processing_time_seconds > 0.5:
                logger.warning(f"🐌 Slow processing: {processing_time_seconds:.2f}s (consider optimizing)")
            else:
                logger.debug(f"⚡ Good performance: {processing_time_seconds:.2f}s")

            return ParsedDocument(content, metadata)

        except Exception as e:
            logger.error(f"❌ Failed to parse raw text '{title}': {e}")
            raise

    def _clean_text_content(self, content: str) -> str:
        """Clean and normalize text content."""
        if not content:
            return ""

        # Remove excessive whitespace
        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            # Remove leading/trailing whitespace
            cleaned_line = line.strip()
            if cleaned_line:
                cleaned_lines.append(cleaned_line)
            elif cleaned_lines and cleaned_lines[-1]:  # Add single empty line between content
                cleaned_lines.append("")

        # Remove trailing empty lines
        while cleaned_lines and not cleaned_lines[-1]:
            cleaned_lines.pop()

        return '\n'.join(cleaned_lines)

    def _detect_language(self, content: str) -> str:
        """Simple language detection based on common patterns."""
        if not content:
            return "unknown"

        # Simple heuristics for common languages
        content_lower = content.lower()

        # English patterns
        english_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
        english_count = sum(1 for word in english_words if word in content_lower)

        # Spanish patterns
        spanish_words = ['el', 'la', 'los', 'las', 'y', 'o', 'pero', 'en', 'con', 'por', 'para', 'de']
        spanish_count = sum(1 for word in spanish_words if word in content_lower)

        # French patterns
        french_words = ['le', 'la', 'les', 'et', 'ou', 'mais', 'en', 'avec', 'pour', 'de', 'du', 'des']
        french_count = sum(1 for word in french_words if word in content_lower)

        # German patterns
        german_words = ['der', 'die', 'das', 'und', 'oder', 'aber', 'in', 'mit', 'für', 'von', 'zu']
        german_count = sum(1 for word in german_words if word in content_lower)

        # Determine language based on word frequency
        if english_count > spanish_count and english_count > french_count and english_count > german_count:
            return "en"
        if spanish_count > french_count and spanish_count > german_count:
            return "es"
        if french_count > german_count:
            return "fr"
        if german_count > 0:
            return "de"
        return "en"  # Default to English

    def _detect_text_structure(self, content: str) -> dict[str, Any]:
        """Detect text structure and formatting patterns."""
        if not content:
            return {}

        lines = content.split('\n')
        structure_info = {
            'paragraphs': 0,
            'empty_lines': 0,
            'potential_headings': 0,
            'bullet_lists': 0,
            'numbered_lists': 0,
            'code_blocks': 0,
            'urls': 0,
            'emails': 0
        }

        current_paragraph_lines = 0
        in_code_block = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                structure_info['empty_lines'] += 1
                if current_paragraph_lines > 0:
                    structure_info['paragraphs'] += 1
                    current_paragraph_lines = 0
            else:
                current_paragraph_lines += 1

                # Code blocks
                if stripped.startswith('```'):
                    in_code_block = not in_code_block
                    if in_code_block:
                        structure_info['code_blocks'] += 1

                if in_code_block:
                    continue

                # Potential headings (short lines that could be titles)
                if len(stripped) < 60 and not stripped.endswith(('.', '!', '?', ':')):
                    structure_info['potential_headings'] += 1

                # Lists
                if stripped.startswith(('-', '*', '•', '◦')):
                    structure_info['bullet_lists'] += 1
                elif stripped[:3].replace('.', '').replace(')', '').isdigit():
                    structure_info['numbered_lists'] += 1

                # URLs and emails
                if 'http' in stripped or 'www.' in stripped:
                    structure_info['urls'] += 1
                if '@' in stripped and '.' in stripped:
                    structure_info['emails'] += 1

        # Add final paragraph if exists
        if current_paragraph_lines > 0:
            structure_info['paragraphs'] += 1

        return structure_info

    async def _detect_language_async(self, content: str) -> str:
        """Async wrapper for language detection."""
        return self._detect_language(content)

    async def _detect_text_structure_async(self, content: str) -> dict[str, Any]:
        """Async wrapper for text structure detection."""
        return self._detect_text_structure(content)
