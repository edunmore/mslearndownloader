"""Main downloader orchestrator."""

import shutil
from pathlib import Path
from typing import Dict, List, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .api_client import MSLearnAPIClient
from .content_scraper import ContentScraper
from .image_handler import ImageHandler
from .formatters import HTMLFormatter, MarkdownFormatter
from .pdf_formatter import PDFFormatter

console = Console()


class MSLearnDownloader:
    """Main downloader class that orchestrates the download process."""
    
    def __init__(self, config):
        """Initialize downloader with configuration."""
        self.config = config
        self.api_client = MSLearnAPIClient(config)
        self.content_scraper = ContentScraper(self.api_client)
        self.image_handler = ImageHandler(self.api_client, config)
    
    def download_course(self, course_url: str, output_format: str, output_dir: str) -> bool:
        """Download all learning paths in a course."""
        learning_path_uids = self.content_scraper.scrape_course_learning_path_uids(course_url)
        
        if not learning_path_uids:
            console.print("[red]No learning paths found in this course[/red]")
            return False
            
        return self._download_course_paths(learning_path_uids, course_url.rstrip('/').split('/')[-1], output_format, output_dir)

    def download_course_by_uid(self, course_uid: str, output_format: str, output_dir: str) -> bool:
        """Download a course by its UID."""
        # Fetch course details
        data = self.api_client.get_catalog(type='courses', uid=course_uid)
        courses = data.get('courses', [])
        if not courses:
            console.print(f"[red]Course not found: {course_uid}[/red]")
            return False
            
        course = courses[0]
        console.print(f"[green]Found course: {course.get('title')}[/green]")
        
        study_guide = course.get('study_guide', [])
        learning_path_uids = [item['uid'] for item in study_guide if item.get('type') == 'learningPath']
        
        if not learning_path_uids:
            console.print("[red]No learning paths found in this course[/red]")
            return False
            
        return self._download_course_paths(learning_path_uids, course_uid, output_format, output_dir)

    def _download_course_paths(self, learning_path_uids: List[str], course_id: str, output_format: str, output_dir: str) -> bool:
        """Helper to download a list of learning paths for a course."""
        console.print(f"[green]Found {len(learning_path_uids)} learning paths in course[/green]")
        
        # Create course subfolder
        import os
        course_output_dir = os.path.join(output_dir, course_id)
        
        success_count = 0
        for i, uid in enumerate(learning_path_uids, 1):
            console.print(f"\n[bold]Processing learning path {i}/{len(learning_path_uids)}: {uid}[/bold]")
            # Recursively call download_learning_path for each path
            if self.download_learning_path(learning_path_uid=uid, output_format=output_format, output_dir=course_output_dir):
                success_count += 1
                
        console.print(f"\n[green]Course download complete. {success_count}/{len(learning_path_uids)} learning paths downloaded successfully.[/green]")
        console.print(f"Location: {course_output_dir}")
        return success_count > 0

    def download_learning_path(self, learning_path_uid: str = None, learning_path_url: str = None,
                               output_format: str = 'pdf', output_dir: str = None) -> bool:
        """Download a learning path by UID or URL."""
        
        # Check if it's a course URL
        if learning_path_url and '/courses/' in learning_path_url:
            return self.download_course(learning_path_url, output_format, output_dir)
        
        # Get learning path metadata
        if learning_path_uid:
            learning_path = self.api_client.get_learning_path_by_uid(learning_path_uid)
        elif learning_path_url:
            learning_path = self.api_client.get_learning_path_from_url(learning_path_url)
        else:
            console.print("[red]Please provide either a UID or URL[/red]")
            return False
        
        if not learning_path:
            return False
        
        console.print(f"[green]Found learning path: {learning_path.get('title')}[/green]")
        console.print(f"Modules: {learning_path.get('number_of_children', 0)}")
    def download_module(self, module_uid: str, output_format: str, output_dir: str) -> bool:
        """Download a single module by UID."""
        # Fetch module details
        data = self.api_client.get_catalog(type='modules', uid=module_uid)
        modules = data.get('modules', [])
        if not modules:
            console.print(f"[red]Module not found: {module_uid}[/red]")
            return False
            
        module = modules[0]
        console.print(f"[green]Found module: {module.get('title')}[/green]")
        
        # Get units for module
        units_by_module = self.api_client.get_units_for_modules([module])
        units = units_by_module.get(module_uid, [])
        
        if not units:
            console.print("[red]No units found for this module[/red]")
            return False
            
        # Scrape content
        modules_content = []
        all_images = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Downloading content...", total=1)
            
            module_data = self.content_scraper.scrape_module_content(module, units)
            modules_content.append(module_data)
            all_images.extend(module_data.get('images', []))
            
            progress.advance(task)
            
        # Download images if enabled
        self._process_images(all_images, modules_content, output_dir)
        
        # Format and save output
        # Wrap in a dummy learning path structure for the formatters
        dummy_lp = {
            'uid': module_uid,
            'title': module.get('title'),
            'summary': module.get('summary'),
            'url': module.get('url'),
            'modules': [module]
        }
        
        self._save_output(dummy_lp, modules_content, output_format, output_dir)
        return True

    def _process_images(self, all_images, modules_content, output_dir):
        """Helper to download and update images."""
        if self.config.get('download.images', True) and all_images:
            output_path = Path(output_dir or self.config.get('storage.output_dir', './downloads'))
            image_url_mapping = self.image_handler.download_images(all_images, output_path)
            
            # Update image paths in content
            for module_data in modules_content:
                for unit_data in module_data['content']:
                    unit_data['html'] = self.image_handler.update_html_image_paths(
                        unit_data['html'], 
                        image_url_mapping,
                        relative_to=output_path,
                        images_subdir='images'
                    )

    def _save_output(self, learning_path, modules_content, output_format, output_dir):
        """Helper to save output in requested formats."""
        output_path = Path(output_dir or self.config.get('storage.output_dir', './downloads'))
        formats = output_format.split(',') if output_format != 'all' else ['html', 'markdown', 'pdf']
        
        if 'html' in formats:
            formatter = HTMLFormatter(output_path)
            formatter.format(learning_path, modules_content)
            
        if 'markdown' in formats or 'md' in formats:
            formatter = MarkdownFormatter(output_path)
            formatter.format(learning_path, modules_content)
            
        if 'pdf' in formats:
            formatter = PDFFormatter(self.config)
            formatter.format(learning_path, modules_content, output_path)

    def download_learning_path(self, learning_path_uid: str = None, learning_path_url: str = None,
                               output_format: str = 'pdf', output_dir: str = None) -> bool:
        """Download a learning path by UID or URL."""
        
        # Check if it's a course URL
        if learning_path_url and '/courses/' in learning_path_url:
            return self.download_course(learning_path_url, output_format, output_dir)
        
        # Get learning path metadata
        if learning_path_uid:
            learning_path = self.api_client.get_learning_path_by_uid(learning_path_uid)
        elif learning_path_url:
            learning_path = self.api_client.get_learning_path_from_url(learning_path_url)
        else:
            console.print("[red]Please provide either a UID or URL[/red]")
            return False
        
        if not learning_path:
            return False
        
        console.print(f"[green]Found learning path: {learning_path.get('title')}[/green]")
        console.print(f"Modules: {learning_path.get('number_of_children', 0)}")
        console.print(f"Duration: {learning_path.get('duration_in_minutes', 0)} minutes")
        console.print()
        
        # Get modules
        modules = self.api_client.get_modules_for_learning_path(learning_path)
        if not modules:
            console.print("[red]No modules found for this learning path[/red]")
            return False
        
        # Get units for all modules
        units_by_module = self.api_client.get_units_for_modules(modules)
        
        # Scrape content for each module
        modules_content = []
        all_images = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Downloading content...", total=len(modules))
            
            for module in modules:
                module_uid = module['uid']
                units = units_by_module.get(module_uid, [])
                
                if units:
                    module_data = self.content_scraper.scrape_module_content(module, units)
                    modules_content.append(module_data)
                    all_images.extend(module_data.get('images', []))
                
                progress.advance(task)
        
        # Download images and save output
        self._process_images(all_images, modules_content, output_dir)
        self._save_output(learning_path, modules_content, output_format, output_dir)
        
        return True
        
        for fmt in formats:
            fmt = fmt.strip().lower()
            if fmt == 'html':
                formatter = HTMLFormatter(self.config)
                formatter.format(learning_path, modules_content, output_path)
            elif fmt == 'markdown' or fmt == 'md':
                formatter = MarkdownFormatter(self.config)
                formatter.format(learning_path, modules_content, output_path)
            elif fmt == 'pdf':
                formatter = PDFFormatter(self.config)
                images_dir = output_path / "images" if image_url_mapping else None
                formatter.format(learning_path, modules_content, output_path, images_dir)
        
        # Cleanup images if requested
        if self.config.get('cleanup.delete_images', False) and image_url_mapping:
            images_dir = output_path / "images"
            if images_dir.exists():
                console.print("[dim]Cleaning up images folder...[/dim]")
                shutil.rmtree(images_dir)

        console.print()
        console.print("[bold green]Download completed successfully![/bold green]")
        return True
