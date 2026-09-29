"""HTML parser with automatic noise removal."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

import trafilatura
from bs4 import BeautifulSoup, NavigableString

from .base_parser import BaseParser, ParsedDocument

logger = logging.getLogger(__name__)


class HTMLParser(BaseParser):
    """Parser for HTML documents with automatic noise removal."""

    def __init__(self):
        super().__init__()
        self.supported_extensions = {'.html', '.htm'}

    async def parse(self, file_path: str, clean_noise: bool = True, **kwargs) -> ParsedDocument:
        """
        Parse HTML document with noise removal.
        
        Args:
            file_path: Path to HTML file
            clean_noise: Whether to automatically remove HTML noise
            **kwargs: Additional parsing options
            
        Returns:
            ParsedDocument with extracted content and metadata
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"HTML file not found: {file_path}")

        filename = Path(file_path).name
        file_size = os.path.getsize(file_path)

        try:
            # Read HTML content
            with open(file_path, encoding='utf-8', errors='ignore') as f:
                html_content = f.read()

            if clean_noise:
                # Use trafilatura for main content extraction if available
                main_content = trafilatura.extract(
                    html_content,
                    include_links=False,
                    include_tables=True,
                    include_formatting=True
                )
                if main_content:
                    extracted_content = main_content
                else:
                    # Fallback to BeautifulSoup cleaning
                    extracted_content = await self._clean_html_content(html_content)
            else:
                # Extract all text without cleaning
                extracted_content = await self._extract_raw_text(html_content)

            # Extract metadata from HTML
            html_metadata = await self._extract_html_metadata(html_content)

            # Create metadata
            metadata = self._create_base_metadata(filename, file_size)
            metadata.update({
                'html_metadata': html_metadata,
                'noise_cleaned': clean_noise,
                'extraction_method': 'trafilatura' if clean_noise else 'beautifulsoup',
                'content_type': 'text/html'
            })

            logger.info(f"Parsed HTML {filename}: {len(extracted_content)} characters")

            return ParsedDocument(extracted_content, metadata)

        except Exception as e:
            logger.error(f"Failed to parse HTML {filename}: {e}")
            raise

    async def _clean_html_content(self, html_content: str) -> str:
        """Clean HTML content using BeautifulSoup."""
        loop = asyncio.get_event_loop()

        # Parse HTML
        soup = await loop.run_in_executor(None, BeautifulSoup, html_content, 'html.parser')

        # Remove unwanted elements
        unwanted_tags = [
            'script', 'style', 'nav', 'header', 'footer', 'aside',
            'advertisement', 'sidebar', 'menu', 'toolbar', 'breadcrumb'
        ]

        for tag_name in unwanted_tags:
            for element in soup.find_all(tag_name):
                element.decompose()

        # Remove elements with unwanted classes/ids
        unwanted_selectors = [
            {'class': lambda x: x and any(cls in ' '.join(x).lower() for cls in [
                'ad', 'advertisement', 'sidebar', 'menu', 'nav', 'footer',
                'header', 'social', 'share', 'comment', 'popup', 'modal'
            ])},
            {'id': lambda x: x and any(cls in x.lower() for cls in [
                'ad', 'advertisement', 'sidebar', 'menu', 'nav', 'footer',
                'header', 'social', 'share', 'comment', 'popup', 'modal'
            ])}
        ]

        for selector in unwanted_selectors:
            for element in soup.find_all(attrs=selector):
                element.decompose()

        # Try to find main content area
        main_content = (
            soup.find('main') or
            soup.find('article') or
            soup.find('div', class_=lambda x: x and 'content' in ' '.join(x).lower()) or
            soup.find('div', id=lambda x: x and 'content' in x.lower()) or
            soup.find('body')
        )

        if main_content:
            # Convert to structured text
            structured_text = await self._html_to_structured_text(main_content, loop)
            return structured_text
        # Fallback to full body text
        return soup.get_text(separator=' ', strip=True)

    async def _html_to_structured_text(self, element, loop) -> str:
        """Convert HTML element to structured text preserving hierarchy."""
        content_parts = []

        for child in element.children:
            if isinstance(child, NavigableString):
                text = child.strip()
                if text:
                    content_parts.append(text)
            else:
                tag_name = child.name.lower()

                if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    # Convert headings to markdown
                    level = int(tag_name[1])
                    heading_text = child.get_text(strip=True)
                    if heading_text:
                        content_parts.append('#' * level + ' ' + heading_text)

                elif tag_name == 'p':
                    # Paragraphs
                    para_text = child.get_text(separator=' ', strip=True)
                    if para_text:
                        content_parts.append(para_text)

                elif tag_name in ['ul', 'ol']:
                    # Lists
                    list_items = []
                    for li in child.find_all('li'):
                        item_text = li.get_text(separator=' ', strip=True)
                        if item_text:
                            list_items.append(f"- {item_text}")
                    if list_items:
                        content_parts.extend(list_items)

                elif tag_name == 'table':
                    # Tables
                    table_text = await self._table_to_text(child, loop)
                    if table_text:
                        content_parts.append(table_text)

                elif tag_name in ['div', 'section', 'article']:
                    # Recurse into container elements
                    nested_text = await self._html_to_structured_text(child, loop)
                    if nested_text:
                        content_parts.append(nested_text)

                else:
                    # Other elements - extract text
                    text = child.get_text(separator=' ', strip=True)
                    if text:
                        content_parts.append(text)

        return '\n\n'.join(content_parts)

    async def _table_to_text(self, table_element, loop) -> str:
        """Convert HTML table to readable text format."""
        try:
            rows = []

            # Process table rows
            for tr in table_element.find_all('tr'):
                cells = []
                for cell in tr.find_all(['td', 'th']):
                    cell_text = cell.get_text(separator=' ', strip=True)
                    cells.append(cell_text)

                if cells:
                    rows.append(cells)

            if not rows:
                return ""

            # Convert to markdown table format
            if len(rows) >= 2:
                # First row as headers
                headers = rows[0]
                data_rows = rows[1:]

                # Ensure consistent column count
                max_cols = max(len(row) for row in rows)

                # Pad headers
                while len(headers) < max_cols:
                    headers.append('')

                table_lines = []
                table_lines.append('| ' + ' | '.join(headers[:max_cols]) + ' |')
                table_lines.append('| ' + ' | '.join(['---'] * max_cols) + ' |')

                for row in data_rows:
                    # Pad row
                    while len(row) < max_cols:
                        row.append('')

                    # Escape pipe characters
                    escaped_row = [cell.replace('|', '\\|') for cell in row[:max_cols]]
                    table_lines.append('| ' + ' | '.join(escaped_row) + ' |')

                return '\n'.join(table_lines)
            # Single row - format as list
            return '\n'.join(f"- {cell}" for cell in rows[0] if cell.strip())

        except Exception as e:
            logger.warning(f"Failed to convert table to text: {e}")
            return table_element.get_text(separator=' ', strip=True)

    async def _extract_raw_text(self, html_content: str) -> str:
        """Extract raw text without cleaning."""
        loop = asyncio.get_event_loop()
        soup = await loop.run_in_executor(None, BeautifulSoup, html_content, 'html.parser')

        # Remove script and style elements
        for element in soup(['script', 'style']):
            element.decompose()

        return soup.get_text(separator=' ', strip=True)

    async def _extract_html_metadata(self, html_content: str) -> dict[str, Any]:
        """Extract metadata from HTML document."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            metadata = {}

            # Title
            title_tag = soup.find('title')
            if title_tag:
                metadata['title'] = title_tag.get_text().strip()

            # Meta tags
            meta_tags = soup.find_all('meta')
            for meta in meta_tags:
                if meta.get('name'):
                    name = meta.get('name').lower()
                    content = meta.get('content', '').strip()
                    if content:
                        metadata[f'meta_{name}'] = content

                elif meta.get('property'):
                    prop = meta.get('property').lower()
                    content = meta.get('content', '').strip()
                    if content:
                        metadata[f'property_{prop}'] = content

            # Language
            html_tag = soup.find('html')
            if html_tag and html_tag.get('lang'):
                metadata['language'] = html_tag.get('lang')

            # Count various elements
            metadata['element_counts'] = {
                'headings': len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])),
                'paragraphs': len(soup.find_all('p')),
                'links': len(soup.find_all('a')),
                'images': len(soup.find_all('img')),
                'tables': len(soup.find_all('table')),
                'lists': len(soup.find_all(['ul', 'ol']))
            }

            return metadata

        except Exception as e:
            logger.warning(f"Failed to extract HTML metadata: {e}")
            return {}

    async def parse_bytes(self, file_bytes: bytes, filename: str, **kwargs) -> ParsedDocument:
        """Parse HTML from bytes."""
        try:
            html_content = file_bytes.decode('utf-8', errors='ignore')

            clean_noise = kwargs.get('clean_noise', True)

            if clean_noise:
                main_content = trafilatura.extract(
                    html_content,
                    include_links=False,
                    include_tables=True,
                    include_formatting=True
                )
                if main_content:
                    extracted_content = main_content
                else:
                    extracted_content = await self._clean_html_content(html_content)
            else:
                extracted_content = await self._extract_raw_text(html_content)

            # Extract metadata
            html_metadata = await self._extract_html_metadata(html_content)

            # Create metadata
            metadata = self._create_base_metadata(filename, len(file_bytes))
            metadata.update({
                'html_metadata': html_metadata,
                'noise_cleaned': clean_noise,
                'extraction_method': 'trafilatura' if clean_noise else 'beautifulsoup',
                'content_type': 'text/html'
            })

            return ParsedDocument(extracted_content, metadata)

        except Exception as e:
            logger.error(f"Failed to parse HTML from bytes: {e}")
            raise
