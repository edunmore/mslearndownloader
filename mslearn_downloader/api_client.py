"""MS Learn Catalog API client."""

import requests
import time
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, quote
from rich.console import Console

console = Console()


class MSLearnAPIClient:
    """Client for interacting with MS Learn Catalog API."""
    
    def __init__(self, config):
        """Initialize API client with configuration."""
        self.config = config
        self.base_url = config.get('api.base_url')
        self.content_base_url = config.get('api.content_base_url')
        self.locale = config.get('api.locale', 'en-us')
        self.timeout = config.get('api.timeout', 30)
        self.retry_attempts = config.get('api.retry_attempts', 5)
        self.retry_delay = config.get('api.retry_delay', 5)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
            'Accept': 'application/json'
        })
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict:
        """Make HTTP request with retry logic."""
        for attempt in range(self.retry_attempts):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                status_code = getattr(e.response, 'status_code', None)
                
                if attempt == self.retry_attempts - 1:
                    console.print(f"[red]Failed to fetch {url}: {e}[/red]")
                    raise
                
                delay = self.retry_delay * (2 ** attempt)
                if status_code == 429:
                    console.print(f"[yellow]Rate limited (429). Waiting {delay}s...[/yellow]")
                else:
                    console.print(f"[yellow]Retry {attempt + 1}/{self.retry_attempts} for {url} (waiting {delay}s)[/yellow]")
                
                time.sleep(delay)
        return {}
    
    def get_catalog(self, **kwargs) -> Dict:
        """Get the full catalog or filtered results."""
        params = {'locale': self.locale}
        params.update(kwargs)
        return self._make_request(self.base_url, params)

    def search_catalog(self, query: str, types: List[str] = None) -> List[Dict]:
        """Search the catalog for items matching a query."""
        if types is None:
            types = ['learningPaths', 'courses']
            
        console.print(f"[cyan]Searching catalog for '{query}' (types: {', '.join(types)})...[/cyan]")
        
        items = []
        for type_name in types:
            data = self.get_catalog(type=type_name)
            items.extend(data.get(type_name, []))
        
        results = []
        query_lower = query.lower()
        # Create a normalized version of the query (remove non-alphanumeric) for fuzzy matching
        # This helps match "PL200" to "PL-200"
        query_normalized = re.sub(r'[^a-z0-9]', '', query_lower)
        
        for item in items:
            title = item.get('title', '').lower()
            summary = item.get('summary', '').lower()
            uid = item.get('uid', '').lower()
            course_number = item.get('course_number', '').lower()
            
            # 1. Direct match
            if (query_lower in title or 
                query_lower in summary or 
                query_lower in uid or 
                query_lower in course_number):
                results.append(item)
                continue
                
            # 2. Normalized match (if query has content)
            if query_normalized:
                # Normalize target fields only if direct match failed
                title_norm = re.sub(r'[^a-z0-9]', '', title)
                summary_norm = re.sub(r'[^a-z0-9]', '', summary)
                uid_norm = re.sub(r'[^a-z0-9]', '', uid)
                course_number_norm = re.sub(r'[^a-z0-9]', '', course_number)
                
                if (query_normalized in title_norm or 
                    query_normalized in summary_norm or 
                    query_normalized in uid_norm or
                    query_normalized in course_number_norm):
                    results.append(item)
                
        return results
    
    def get_learning_path_by_uid(self, uid: str) -> Optional[Dict]:
        """Get a specific learning path by its UID."""
        console.print(f"[cyan]Fetching learning path: {uid}[/cyan]")
        
        # Fetch catalog filtered by learning paths
        data = self.get_catalog(type='learningPaths', uid=uid)
        
        learning_paths = data.get('learningPaths', [])
        if not learning_paths:
            console.print(f"[red]Learning path not found: {uid}[/red]")
            return None
        
        return learning_paths[0]
    
    def get_learning_path_from_url(self, url: str) -> Optional[Dict]:
        """Extract UID from URL and get learning path."""
        # Extract UID from URL like: /training/paths/az-400-work-git-for-enterprise-devops/
        parts = url.rstrip('/').split('/')
        
        # Find the path segment
        if 'paths' in parts:
            idx = parts.index('paths')
            if idx + 1 < len(parts):
                path_slug = parts[idx + 1]
                # Construct UID (usually learn.{path-slug})
                uid = f"learn.{path_slug}"
                return self.get_learning_path_by_uid(uid)
        
        console.print(f"[red]Could not extract learning path UID from URL: {url}[/red]")
        return None
    
    def get_modules_for_learning_path(self, learning_path: Dict) -> List[Dict]:
        """Get all modules associated with a learning path."""
        module_uids = learning_path.get('modules', [])
        if not module_uids:
            return []
        
        console.print(f"[cyan]Fetching {len(module_uids)} modules...[/cyan]")
        
        # Fetch modules by UIDs
        uid_param = ','.join(module_uids)
        data = self.get_catalog(type='modules', uid=uid_param)
        
        modules = data.get('modules', [])
        
        # Sort modules in the order they appear in the learning path
        module_dict = {m['uid']: m for m in modules}
        sorted_modules = []
        for uid in module_uids:
            if uid in module_dict:
                sorted_modules.append(module_dict[uid])
        
        return sorted_modules
    
    def get_units_for_modules(self, modules: List[Dict]) -> Dict[str, List[Dict]]:
        """Get all units for a list of modules."""
        # Collect all unit UIDs
        all_unit_uids = []
        module_unit_map = {}
        
        for module in modules:
            unit_uids = module.get('units', [])
            all_unit_uids.extend(unit_uids)
            module_unit_map[module['uid']] = unit_uids
        
        if not all_unit_uids:
            return {}
        
        console.print(f"[cyan]Fetching {len(all_unit_uids)} units...[/cyan]")
        
        # Fetch units in batches to avoid URL length limits
        # API has URL length limits, so batch requests
        batch_size = 10
        all_units = []
        
        for i in range(0, len(all_unit_uids), batch_size):
            batch = all_unit_uids[i:i+batch_size]
            uid_param = ','.join(batch)
            try:
                data = self.get_catalog(type='units', uid=uid_param)
                all_units.extend(data.get('units', []))
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to fetch batch of units: {e}[/yellow]")
                # Continue with other batches
        
        unit_dict = {u['uid']: u for u in all_units}
        
        # Organize units by module
        result = {}
        for module_uid, unit_uids in module_unit_map.items():
            result[module_uid] = [unit_dict[uid] for uid in unit_uids if uid in unit_dict]
        
        return result
    
    def fetch_content(self, url: str, silent: bool = False) -> str:
        """Fetch HTML content from a URL with retries."""
        for attempt in range(self.retry_attempts):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except requests.exceptions.RequestException as e:
                # If it's a 404, don't retry, just return empty (unless we want to be sure)
                # But for 429 (Too Many Requests) or 5xx, we should retry.
                status_code = getattr(e.response, 'status_code', None)
                
                if status_code == 404:
                    if not silent:
                        console.print(f"[red]Failed to fetch content from {url}: 404 Not Found[/red]")
                    return ""
                
                if attempt == self.retry_attempts - 1:
                    if not silent:
                        console.print(f"[red]Failed to fetch content from {url}: {e}[/red]")
                    return ""
                
                # Backoff for 429
                delay = self.retry_delay
                if status_code == 429:
                    delay *= 2  # Double delay for rate limits
                    if not silent:
                        console.print(f"[yellow]Rate limited (429). Waiting {delay}s...[/yellow]")
                elif not silent:
                    console.print(f"[yellow]Retry {attempt + 1}/{self.retry_attempts} for {url}[/yellow]")
                
                time.sleep(delay)
        return ""
    
    def download_image(self, url: str, referer: Optional[str] = None) -> Optional[bytes]:
        """Download an image with retries and return bytes."""
        headers = {
            'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8'
        }
        if referer:
            headers['Referer'] = referer
        for attempt in range(self.retry_attempts):
            try:
                response = self.session.get(url, timeout=self.timeout, headers=headers)
                response.raise_for_status()
                return response.content
            except requests.exceptions.RequestException as e:
                if attempt == self.retry_attempts - 1:
                    console.print(f"[yellow]Failed to download image {url}: {e}[/yellow]")
                    return None
                time.sleep(self.retry_delay)
