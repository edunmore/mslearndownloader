"""Content scraper for MS Learn pages."""

from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
import re
from rich.console import Console

console = Console()


class ContentScraper:
    """Scraper for extracting content from MS Learn pages."""
    
    def __init__(self, api_client):
        """Initialize scraper with API client."""
        self.api_client = api_client
    
    def scrape_module_content(self, module: Dict, units: List[Dict]) -> Dict:
        """Scrape content for a module and its units."""
        console.print(f"[cyan]Scraping module: {module.get('title')}[/cyan]")
        
        result = {
            'metadata': module,
            'content': [],
            'images': []
        }
        
        # Pre-fetch module page to resolve exact unit URLs
        unit_urls = {}
        module_url = module.get('url', '')
        if module_url:
            try:
                module_html = self.api_client.fetch_content(module_url, silent=True)
                if module_html:
                    soup = BeautifulSoup(module_html, 'lxml')
                    for li in soup.find_all('li', class_='module-unit'):
                        uid = li.get('data-unit-uid')
                        link = li.find('a', class_='unit-title')
                        if uid and link and link.get('href'):
                            # Resolve relative URL
                            # Note: module_url might have query params, split them off
                            base_url = module_url.split('?')[0]
                            if not base_url.endswith('/'):
                                base_url += '/'
                            absolute_url = urljoin(base_url, link.get('href'))
                            unit_urls[uid] = absolute_url
            except Exception as e:
                console.print(f"[yellow]Failed to parse module page for unit URLs: {e}[/yellow]")

        # Scrape each unit
        for i, unit in enumerate(units, 1):
            console.print(f"  [dim]Unit {i}/{len(units)}: {unit.get('title')}[/dim]")
            
            # Pass the pre-resolved URL if available
            known_url = unit_urls.get(unit.get('uid'))
            
            unit_content = self._scrape_unit(module, unit, i, known_url)
            if unit_content:
                result['content'].append(unit_content)
                result['images'].extend(unit_content.get('images', []))
        
        return result
    
    def _scrape_unit(self, module: Dict, unit: Dict, unit_number: int, known_url: Optional[str] = None) -> Optional[Dict]:
        """Scrape content for a single unit with fallbacks for slug patterns."""
        module_url = module.get('url', '')
        unit_uid = unit.get('uid', '')
        title = unit.get('title', '')

        html = ''
        unit_url = ''

        # If we have a known URL from the module page, try it first
        if known_url:
            html = self.api_client.fetch_content(known_url, silent=True)
            if html and not self._is_404_page(html):
                unit_url = known_url
        
        # If known URL failed or wasn't provided, try guessing
        if not unit_url:
            unit_parts = unit_uid.split('.')
            if len(unit_parts) < 3:
                console.print(f"[yellow]Could not construct URL for unit: {unit_uid}[/yellow]")
                return None

            unit_slug = unit_parts[-1]
            base_url = module_url.split('?')[0].rstrip('/')

            # Try several slug patterns until content is found
            # Common patterns:
            # 1. {number}-{slug} (e.g., 1-introduction)
            # 2. {number}-{title-slug} (e.g., 1-introducing-power-automate)
            # 3. {slug} (e.g., introduction)
            # 4. {title-slug} (e.g., introducing-power-automate)
            # 5. {number}-{short-slug} (e.g., 1-introduction where slug was flow-introduction)
            
            # Helper to clean slug (remove prefixes like 'flow-', 'power-apps-', etc.)
            def clean_slug(s):
                return re.sub(r'^(flow|power-apps|canvas-apps|model-driven-apps)-', '', s)

            candidates = [
                f"{unit_number}-{unit_slug}",
                f"{unit_number}-{self._slugify(title)}" if title else None,
                unit_slug,
                self._slugify(title) if title else None,
                # Add cleaned versions
                f"{unit_number}-{clean_slug(unit_slug)}",
                clean_slug(unit_slug),
                # Try just the number + introduction (common pattern)
                f"{unit_number}-introduction",
            ]
            # Deduplicate while preserving order
            candidates = list(dict.fromkeys([c for c in candidates if c]))

            for slug in candidates:
                candidate_url = f"{base_url}/{slug}"
                # Use silent=True to avoid spamming 404 errors during probing
                html = self.api_client.fetch_content(candidate_url, silent=True)
                if html and not self._is_404_page(html):
                    unit_url = candidate_url
                    break
        
        if not html or self._is_404_page(html):
            console.print(f"[yellow]No valid HTML for unit: {unit_uid} (tried known URL and guesses)")
            return None

        soup = BeautifulSoup(html, 'lxml')
        main_content = self._extract_main_content(soup)
        if not main_content:
            console.print(f"[yellow]Could not find main content for unit: {unit_url}")

        images = self._extract_images(main_content, unit_url) if main_content else []
        html_fragment = str(main_content) if main_content else ''
        text_fragment = main_content.get_text(strip=False) if main_content else ''
        console.print(f"    [dim]Extracted HTML chars: {len(html_fragment)}, text chars: {len(text_fragment)}[/dim]")

        return {
            'metadata': unit,
            'url': unit_url,
            'html': html_fragment,
            'text': text_fragment,
            'images': images
        }

    def scrape_course_learning_path_uids(self, course_url: str) -> List[str]:
        """Scrape learning path UIDs from a course page."""
        console.print(f"[cyan]Scraping course page: {course_url}[/cyan]")
        
        html = self.api_client.fetch_content(course_url)
        if not html:
            return []
            
        soup = BeautifulSoup(html, 'lxml')
        
        # Find all articles with data-learn-uid
        uids = []
        seen_uids = set()
        
        for article in soup.find_all('article', attrs={'data-learn-uid': True}):
            uid = article['data-learn-uid']
            if uid and uid not in seen_uids:
                uids.append(uid)
                seen_uids.add(uid)
        
        console.print(f"[green]Found {len(uids)} learning paths[/green]")
        return uids
    
    def _extract_main_content(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """Extract the main content area from the page."""
        candidates = [
            'main .content',
            'main article',
            'main [data-bi-name="content"], main [role="main"]',
            'article',
            'main'
        ]
        for selector in candidates:
            content = soup.select_one(selector)
            if content:
                self._format_quiz(content, soup)
                self._clean_content(content)
                return content
        return None
    
    def _format_quiz(self, content: BeautifulSoup, soup: BeautifulSoup):
        """Transform hidden quiz forms into visible static content."""
        quiz_form = content.select_one('#question-container')
        if not quiz_form:
            return

        # Create a container for the formatted quiz
        quiz_div = soup.new_tag('div')
        quiz_div['class'] = 'formatted-quiz'
        
        questions = quiz_form.select('.quiz-question')
        for q in questions:
            # Extract question
            q_title_div = q.select_one('.quiz-question-title')
            if not q_title_div:
                continue
                
            # Get the question text (ignoring the number span if possible)
            q_text_p = q_title_div.select_one('p')
            q_text = q_text_p.get_text(strip=True) if q_text_p else q_title_div.get_text(strip=True)
            
            # Create question header
            q_header = soup.new_tag('h3')
            q_header.string = f"Question: {q_text}"
            quiz_div.append(q_header)
            
            # Extract answers
            answers_ul = soup.new_tag('ul')
            choices = q.select('.quiz-choice')
            for choice in choices:
                choice_text_div = choice.select_one('.radio-label-text')
                if choice_text_div:
                    choice_text = choice_text_div.get_text(strip=True)
                    li = soup.new_tag('li')
                    li.string = choice_text
                    answers_ul.append(li)
            
            quiz_div.append(answers_ul)
            quiz_div.append(soup.new_tag('hr'))

        # Replace the form with the formatted div
        quiz_form.replace_with(quiz_div)

    def _clean_content(self, content: BeautifulSoup):
        """Remove unwanted elements from content."""
        # Remove elements
        unwanted_selectors = [
            'nav',
            'header',
            'footer',
            '.nav',
            '.navigation',
            '.feedback',
            '.page-metadata',
            '.contributors',
            '.alert-banner',
            '[data-bi-name="feedback"]',
            '.margin-note',
            '.is-invisible'
        ]
        
        for selector in unwanted_selectors:
            for element in content.select(selector):
                element.decompose()
        
        # Remove script and style tags
        for tag in content.find_all(['script', 'style']):
            tag.decompose()
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract all images from the content."""
        images = []
        
        for img in soup.find_all('img'):
            src = img.get('src', '') or img.get('data-src', '') or img.get('data-original', '')
            if not src:
                continue
            
            # Make URL absolute first
            absolute_url = urljoin(base_url, src)
            
            # Get attributes
            role = img.get('role', '')
            alt = img.get('alt', '')
            width = img.get('width')
            height = img.get('height')
            
            # Skip presentation/decorative images (no alt text and has role attribute)
            if role == 'presentation':
                continue
            
            # Filter out non-content images (badges, icons, etc.)
            if '/achievements/' in absolute_url or '/badges/' in absolute_url:
                continue
            
            # Accept images with alt text (content images)
            # Or images without role attribute (might be content)
            if alt or not role:
                images.append({
                    'url': absolute_url,
                    'alt': alt,
                    'width': width,
                    'height': height,
                    'original_src': src,
                    'referer': base_url
                })
        
        return images
    
    def convert_to_markdown(self, html_content: str) -> str:
        """Convert HTML content to Markdown."""
        from markdownify import markdownify as md
        
        # Convert HTML to Markdown
        markdown = md(html_content, heading_style="ATX", code_language="python")
        
        # Clean up extra whitespace
        markdown = re.sub(r'\n\n\n+', '\n\n', markdown)
        
        return markdown

    def _slugify(self, text: str) -> str:
        """Create a URL-friendly slug from text."""
        text = text.lower()
        text = re.sub(r'[^a-z0-9]+', '-', text)
        return text.strip('-')

    def _is_404_page(self, html: str) -> bool:
        """Detect Microsoft Learn 404 responses by content markers."""
        markers = ['404 - Page not found', 'We couldn\'t find this page']
        return any(m.lower() in html.lower() for m in markers)
