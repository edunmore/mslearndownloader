"""Command-line interface for MS Learn Downloader."""

import click
from pathlib import Path
from rich.console import Console

from .config import Config
from .downloader import MSLearnDownloader

console = Console()


@click.command()
@click.option('--url', '-u', help='Learning path URL')
@click.option('--uid', help='Learning path UID (e.g., learn.az-400-work-git-for-enterprise-devops)')
@click.option('--format', '-f', 'output_format', 
              default='pdf',
              type=click.Choice(['html', 'markdown', 'md', 'pdf', 'all'], case_sensitive=False),
              help='Output format (default: pdf)')
@click.option('--output', '-o', 'output_dir',
              default='./downloads',
              help='Output directory (default: ./downloads)')
@click.option('--config', '-c', 'config_file',
              default='config.yaml',
              help='Configuration file path (default: config.yaml)')
@click.option('--no-images', is_flag=True, help='Skip downloading images')
@click.option('--delete-images', is_flag=True, help='Delete images folder after PDF generation')
@click.option('--search', '-s', help='Search for learning paths by keyword')
@click.option('--download-all', is_flag=True, help='Download all found learning paths (use with --search)')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompts')
@click.version_option(version='1.0.0')
def main(url, uid, output_format, output_dir, config_file, no_images, delete_images, search, download_all, yes):
    """
    MS Learn Downloader - Download learning paths from Microsoft Learn.
    
    Examples:
    
      Search for learning paths:
      
        mslearn-dl --search "AZ-400"

      Download all search results:
      
        mslearn-dl --search "AZ-400" --download-all

      Download by URL to PDF:
      
        mslearn-dl --url "https://learn.microsoft.com/training/paths/az-400-work-git-for-enterprise-devops/" --format pdf
      
      Download by UID to all formats:
      
        mslearn-dl --uid "learn.az-400-work-git-for-enterprise-devops" --format all
      
      Download to specific directory:
      
        mslearn-dl --url "..." --output ./my-downloads
    """
    
    # Display banner
    console.print("[bold blue]MS Learn Downloader v1.0.0[/bold blue]")
    console.print()
    
    # Validate input
    if not url and not uid and not search:
        console.print("[red]Error: Please provide either --url, --uid, or --search[/red]")
        console.print("Use --help for usage information")
        return
    
    # Load configuration
    try:
        config = Config(config_file)
        
        # Override config with CLI options
        if no_images:
            config.set('download.images', False)
        if delete_images:
            config.set('cleanup.delete_images', True)
        
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        console.print("Using default configuration...")
        config = Config()
    
    # Create downloader
    downloader = MSLearnDownloader(config)

    # Search mode
    if search:
        # Search for learning paths, courses, and modules
        results = downloader.api_client.search_catalog(search, types=['learningPaths', 'courses', 'modules'])
        if not results:
            console.print(f"[yellow]No items found matching '{search}'[/yellow]")
        else:
            console.print(f"[green]Found {len(results)} items matching '{search}':[/green]")
            console.print()
            
            from rich.table import Table
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Type", style="cyan")
            table.add_column("Title")
            table.add_column("UID", style="dim")
            table.add_column("Duration (min)", justify="right")
            
            for item in results:
                # Determine type label
                item_type = item.get('type', 'Unknown')
                if item_type == 'learningPath':
                    type_label = "Path"
                elif item_type == 'course':
                    type_label = "Course"
                elif item_type == 'module':
                    type_label = "Module"
                else:
                    type_label = item_type

                table.add_row(
                    type_label,
                    item.get('title', 'N/A'),
                    item.get('uid', 'N/A'),
                    str(item.get('duration_in_minutes', 0) or item.get('duration_in_hours', 0) * 60)
                )
            
            console.print(table)
            
            if download_all:
                if not yes and not click.confirm(f"\nDo you want to download all {len(results)} items?"):
                    return

                import re
                # Sanitize search term for folder name
                safe_search = re.sub(r'[^a-zA-Z0-9\s]', '', search).strip()
                search_output_dir = Path(output_dir) / safe_search
                
                console.print(f"\n[bold]Starting batch download to: {search_output_dir}[/bold]")
                
                success_count = 0
                for i, item in enumerate(results, 1):
                    console.print(f"\n[bold cyan]Processing {i}/{len(results)}: {item['title']} ({item.get('type')})[/bold cyan]")
                    try:
                        if item.get('type') == 'course':
                            if downloader.download_course_by_uid(
                                course_uid=item['uid'],
                                output_format=output_format,
                                output_dir=str(search_output_dir)
                            ):
                                success_count += 1
                        elif item.get('type') == 'module':
                            if downloader.download_module(
                                module_uid=item['uid'],
                                output_format=output_format,
                                output_dir=str(search_output_dir)
                            ):
                                success_count += 1
                        else:
                            if downloader.download_learning_path(
                                learning_path_uid=item['uid'], 
                                output_format=output_format, 
                                output_dir=str(search_output_dir)
                            ):
                                success_count += 1
                    except Exception as e:
                        console.print(f"[red]Failed to download {item['uid']}: {e}[/red]")
                
                console.print(f"\n[green]Batch download complete. {success_count}/{len(results)} items downloaded successfully.[/green]")

        return
    
    # Download
    try:
        success = downloader.download_learning_path(
            learning_path_uid=uid,
            learning_path_url=url,
            output_format=output_format,
            output_dir=output_dir
        )
        
        if not success:
            exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Download interrupted by user[/yellow]")
        exit(1)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        exit(1)


if __name__ == '__main__':
    main()
