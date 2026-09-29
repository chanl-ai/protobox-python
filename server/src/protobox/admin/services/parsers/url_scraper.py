"""Enhanced URL scraper with depth-limited crawling, comprehensive logging, and standardized output."""

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import aiohttp
import trafilatura
from bs4 import BeautifulSoup
from loguru import logger
from trafilatura.settings import use_config

from protobox.admin.config import settings

from .base_parser import BaseParser, ParsedDocument


class URLScraper(BaseParser):
    """URL scraper with depth-limited crawling and content extraction."""

    def __init__(self):
        super().__init__()
        self.supported_extensions = {'.html', '.htm', '.php', '.jsp', '.asp'}
        self.timeout = settings.page_retrieval_timeout
        self.max_content_size = settings.max_content_size
        self.max_page_size = settings.max_page_size

        # Configure trafilatura for better extraction
        self.trafilatura_config = use_config()
        self.trafilatura_config.set('DEFAULT', 'EXTRACTION_TIMEOUT', str(self.timeout))

    async def parse(self, url: str, **kwargs) -> ParsedDocument:
        """
        Scrape a single URL with comprehensive logging and standardized output.
        
        Args:
            url: URL to scrape
            **kwargs: Additional scraping options
            
        Returns:
            ParsedDocument with scraped content and metadata
        """
        start_time = datetime.now(UTC)

        logger.info(f"🌐 Starting single URL scraping for {url}")

        try:
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid URL: {url}")

            logger.info(f"🔍 Validated URL: {parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}")

            # Create HTTP session with appropriate settings
            logger.debug(f"🔧 Creating HTTP session with timeout: {self.timeout}s")
            connector = aiohttp.TCPConnector(limit=3, limit_per_host=1)
            timeout_config = aiohttp.ClientTimeout(total=self.timeout * 2, connect=self.timeout)

            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout_config,
                headers={
                    'User-Agent': 'ProtoBox Knowledge Base Scraper 2.0',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive'
                }
            ) as session:

                # Scrape single page with timeout protection
                logger.info(f"🚀 Starting single page scraping from {url}")
                try:
                    page_data = await self._run_with_timeout(
                        self._fetch_and_parse_page(session, url)
                    )
                except TimeoutError:
                    logger.warning(f"⏰ URL scraping timed out after {self.processing_timeout}s")
                    raise Exception(f"URL scraping timed out after {self.processing_timeout}s")

                if not page_data:
                    raise Exception("No content extracted from URL")

                # Calculate processing time
                end_time = datetime.now(UTC)
                processing_time_seconds = (end_time - start_time).total_seconds()

                # Create comprehensive metadata
                metadata = self._create_base_metadata(url, len(page_data['content']))
                metadata.update({
                    'source_type': 'url',
                    'original_url': url,
                    'page_title': page_data.get('title', ''),
                    'content_size': len(page_data['content']),
                    'domain': parsed_url.netloc,
                    'scraping_timestamp': end_time.isoformat(),
                    'content_type': 'text/html',
                    'processing_time_seconds': processing_time_seconds,
                    'parser_version': '2.0.0',
                    'extraction_timestamp': end_time.isoformat(),
                    'warnings': [],
                    'errors': []
                })

                # Enhanced completion logging
                logger.info(f"✅ URL scraping complete for {url}: {processing_time_seconds:.2f}s")
                logger.info(f"📊 Scraping results: {len(page_data['content']):,} characters extracted")
                logger.info(f"📝 Page title: {page_data.get('title', 'No title')}")

                # Log domain insights
                logger.info(f"🌍 Domain: {parsed_url.netloc}")

                # Performance insights
                if processing_time_seconds > 10.0:
                    logger.warning(f"🐌 Slow scraping: {processing_time_seconds:.2f}s")
                else:
                    logger.debug(f"⚡ Fast scraping: {processing_time_seconds:.2f}s")

                # Content quality insights
                if len(page_data['content']) < 1000:
                    logger.warning(f"⚠️ Low content extracted: {len(page_data['content']):,} chars (URL may be empty or blocked)")
                elif len(page_data['content']) > 100000:
                    logger.info(f"🎯 Rich content extracted: {len(page_data['content']):,} chars")

                return ParsedDocument(page_data['content'], metadata)

        except Exception as e:
            logger.error(f"❌ Failed to scrape URL {url}: {e}")
            raise



    async def _fetch_and_parse_page(self, session: aiohttp.ClientSession, url: str) -> dict[str, Any] | None:
        """Fetch and parse a single page."""
        try:
            logger.debug(f"📥 Fetching {url}")
            async with session.get(url) as response:
                # Check response status
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {response.reason}")

                logger.debug(f"✅ HTTP {response.status} response received")

                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if 'html' not in content_type:
                    raise Exception(f"Non-HTML content type: {content_type}")

                logger.debug(f"📄 Content type: {content_type}")

                # Check content size
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > self.max_page_size:
                    raise Exception(f"Page too large: {content_length:,} bytes")

                # Read content with size limit
                content = await response.read()
                if len(content) > self.max_page_size:
                    raise Exception(f"Page content too large: {len(content):,} bytes")

                logger.debug(f"📖 Content downloaded: {len(content):,} bytes")

                html_content = content.decode('utf-8', errors='ignore')

                # Extract main content using trafilatura
                logger.debug("🔧 Extracting content using trafilatura")
                main_content = trafilatura.extract(
                    html_content,
                    config=self.trafilatura_config,
                    include_links=False,
                    include_tables=True,
                    include_formatting=True
                )

                if not main_content or len(main_content.strip()) < 50:
                    raise Exception("No meaningful content extracted")

                logger.debug(f"📝 Content extracted: {len(main_content):,} characters")

                # Extract metadata and links
                logger.debug("🔍 Extracting metadata and links")
                soup = BeautifulSoup(html_content, 'html.parser')
                page_metadata = self._extract_page_metadata(soup, url)

                logger.debug(f"📋 Metadata extracted: {len(page_metadata)} fields")

                return {
                    'url': url,
                    'title': page_metadata.get('title', ''),
                    'content': main_content,
                    'metadata': page_metadata,
                    'content_size': len(main_content),
                    'scraped_at': datetime.now(UTC).isoformat()
                }

        except TimeoutError:
            logger.warning(f"⏰ Timeout while fetching {url}")
            raise Exception("Request timeout")
        except Exception as e:
            logger.warning(f"❌ Failed to fetch {url}: {e}")
            raise Exception(f"Failed to fetch page: {e}")

    def _extract_with_beautifulsoup(self, html_content: str) -> str:
        """Fallback content extraction using BeautifulSoup."""
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove script, style, and other non-content elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()

        # Try to find main content area
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')

        if main_content:
            return main_content.get_text(separator=' ', strip=True)
        # Fall back to body content
        body = soup.find('body')
        if body:
            return body.get_text(separator=' ', strip=True)
        return soup.get_text(separator=' ', strip=True)

    def _extract_page_metadata(self, soup: BeautifulSoup, url: str) -> dict[str, Any]:
        """Extract metadata from HTML page."""
        metadata = {'url': url}

        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text().strip()

        # Meta tags
        description_tag = soup.find('meta', attrs={'name': 'description'})
        if description_tag:
            metadata['description'] = description_tag.get('content', '').strip()

        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_tag:
            metadata['keywords'] = keywords_tag.get('content', '').strip()

        author_tag = soup.find('meta', attrs={'name': 'author'})
        if author_tag:
            metadata['author'] = author_tag.get('content', '').strip()

        # Open Graph tags
        og_title = soup.find('meta', property='og:title')
        if og_title:
            metadata['og_title'] = og_title.get('content', '').strip()

        og_description = soup.find('meta', property='og:description')
        if og_description:
            metadata['og_description'] = og_description.get('content', '').strip()

        # Language
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            metadata['language'] = html_tag.get('lang')

        return metadata
