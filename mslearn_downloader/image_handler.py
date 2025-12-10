"""Image downloader and handler."""

import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
from rich.console import Console
from concurrent.futures import ThreadPoolExecutor, as_completed

console = Console()


class ImageHandler:
    """Handler for downloading and managing images."""
    
    def __init__(self, api_client, config):
        """Initialize image handler."""
        self.api_client = api_client
        self.config = config
        self.max_workers = config.get('download.max_concurrent_downloads', 5)
    
    def download_images(self, images: List[Dict], output_dir: Path) -> Dict[str, str]:
        """Download all images and return a mapping of original URL to local path."""
        if not images:
            return {}
        
        output_dir = Path(output_dir)
        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        console.print(f"[cyan]Downloading {len(images)} images...[/cyan]")
        
        url_to_path = {}
        
        # Download images concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_image = {
                executor.submit(self._download_single_image, img, images_dir): img 
                for img in images
            }
            
            for future in as_completed(future_to_image):
                image = future_to_image[future]
                try:
                    result = future.result()
                    if result:
                        url_to_path[image['url']] = result
                except Exception as e:
                    console.print(f"[red]Error downloading {image['url']}: {e}[/red]")
        
        console.print(f"[green]Downloaded {len(url_to_path)} images successfully[/green]")
        return url_to_path
    
    def _download_single_image(self, image: Dict, images_dir: Path) -> Optional[str]:
        """Download a single image."""
        url = image['url']
        
        # Generate filename from URL hash
        filename = self._generate_filename(url)
        filepath = images_dir / filename
        
        # Skip if already exists
        if filepath.exists():
            return str(filepath)
        
        # Download image
        image_data = self.api_client.download_image(url, referer=image.get('referer'))
        if not image_data:
            return None
        
        # Save image
        try:
            with open(filepath, 'wb') as f:
                f.write(image_data)
            return str(filepath)
        except Exception as e:
            console.print(f"[red]Failed to save image {filename}: {e}[/red]")
            return None
    
    def _generate_filename(self, url: str) -> str:
        """Generate a filename for an image URL."""
        parsed = urlparse(url)
        path = parsed.path
        
        # Get extension from URL
        ext = Path(path).suffix
        if not ext or len(ext) > 5:
            ext = '.png'  # Default extension
        
        # Get original filename
        original_name = Path(path).stem
        
        # Create hash of URL for uniqueness
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        
        # Combine original name with hash
        if original_name:
            # Sanitize original name
            original_name = "".join(c for c in original_name if c.isalnum() or c in ('-', '_'))
            filename = f"{original_name}_{url_hash}{ext}"
        else:
            filename = f"image_{url_hash}{ext}"
        
        return filename
    
    def update_html_image_paths(
        self,
        html_content: str,
        url_mapping: Dict[str, str],
        relative_to: Optional[Path] = None,
        images_subdir: str = "images",
    ) -> str:
        """Update image paths in HTML content to point to local files.

        images_subdir lets us keep HTML references like images/<file>.png so the
        HTML can be opened directly alongside the images folder.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, 'lxml')

        # Precompute lookup maps for speed and reliability
        name_map = {}
        for original_url, local_path in url_mapping.items():
            fname_local = Path(local_path).name
            name_map[fname_local] = local_path
            # also map the original filename from the URL (without hash) so relative src can be resolved
            url_path_name = Path(urlparse(original_url).path).name
            if url_path_name:
                name_map[url_path_name] = local_path

        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-original') or ''
            if not src:
                continue

            chosen_local = None
            # First pass: exact/substring match on full URL
            for url, local_path in url_mapping.items():
                if url in src or src in url:
                    chosen_local = local_path
                    break
            # Second pass: basename match
            if not chosen_local:
                fname = Path(src).name
                if fname in name_map:
                    chosen_local = name_map[fname]

            if chosen_local:
                local_path = Path(chosen_local)
                if images_subdir:
                    # Use POSIX-style paths so browsers render from file://
                    img['src'] = f"{images_subdir}/{local_path.name}"
                else:
                    img['src'] = local_path.name
                # remove lazy-loading attributes to avoid stale URLs
                for attr in ('data-src', 'data-original'): 
                    if attr in img.attrs:
                        img.attrs.pop(attr, None)

        return str(soup)
    
    def update_markdown_image_paths(self, markdown_content: str, url_mapping: Dict[str, str], images_subdir: str = "images") -> str:
        """Update image paths in Markdown content to point to local files."""
        import re
        
        # Match markdown image syntax: ![alt](url)
        def replace_image(match):
            alt = match.group(1)
            url = match.group(2)
            
            # Find matching local path
            for original_url, local_path in url_mapping.items():
                if url in original_url or original_url in url:
                    local_path = Path(local_path)
                    if images_subdir:
                        return f"![{alt}]({Path(images_subdir) / local_path.name})"
                    return f"![{alt}]({local_path.name})"
            
            return match.group(0)
        
        markdown_content = re.sub(r'!\[([^\]]*)\]\(([^\)]+)\)', replace_image, markdown_content)
        
        return markdown_content
