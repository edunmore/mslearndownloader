# MS Learn Downloader - Agent Guide

This document is designed to help AI agents understand the architecture, purpose, and usage of the `mslearn-downloader` project.

## Project Overview

**MS Learn Downloader** is a Python-based tool designed to download learning paths, courses, and modules from Microsoft Learn. It converts the online content into offline-friendly formats: **PDF**, **Markdown**, and **HTML**.

**Primary Use Case:** The tool was built to generate consolidated PDFs for ingestion into **NotebookLM**, enabling customized, AI-driven learning experiences for students and certification candidates.

## Architecture

The project is structured as a Python package `mslearn_downloader` with a CLI entry point.

### Core Modules (`mslearn_downloader/`)

| Module | Purpose | Key Classes/Functions |
| :--- | :--- | :--- |
| `api_client.py` | Interacts with the MS Learn Catalog API to fetch metadata. | `MSLearnAPI` |
| `content_scraper.py` | Scrapes and cleans HTML content from module pages. | `ContentScraper` |
| `downloader.py` | Orchestrates the download process (fetching metadata, scraping content, saving files). | `MSLearnDownloader` |
| `pdf_formatter.py` | Generates PDFs using **Playwright** (Chromium). | `PDFFormatter` |
| `image_handler.py` | Downloads and processes images (including SVG to PNG conversion). | `ImageHandler` |
| `formatters.py` | Handles HTML and Markdown formatting. | `HTMLFormatter`, `MarkdownFormatter` |
| `cli.py` | Implements the Command Line Interface using `click`. | `main` command |
| `config.py` | Manages configuration loading from `config.yaml`. | `Config` |

### Entry Points

- **`main.py`**: The primary entry point for the CLI.
- **`download_all_az400.py`**: A specific script to batch download AZ-400 related paths.

## Key Technologies & Dependencies

- **Playwright**: Used for high-fidelity PDF generation. It renders the HTML in a headless Chromium browser to ensure the output looks exactly like the web page.
- **BeautifulSoup4**: Used for parsing and cleaning the raw HTML content from MS Learn.
- **CairoSVG**: Used to convert SVG images to PNG, as some PDF renderers struggle with SVGs. **Note:** Requires GTK3 runtime on Windows.
- **Click**: Used for building the CLI.
- **Rich**: Used for pretty terminal output.

## Configuration

The project uses `config.yaml` for settings. Key sections:
- `api`: Base URLs and timeouts.
- `download`: Toggles for images, exercises, code samples.
- `output`: Default format and PDF settings (page size, margins).
- `storage`: Directory paths.

## Common Workflows

### 1. Downloading a Learning Path
The agent typically invokes `main.py` with a URL or UID.
```bash
python main.py --url "https://learn.microsoft.com/..." --format pdf
```

### 2. Searching
```bash
python main.py --search "AZ-400"
```

### 3. PDF Generation Logic
1.  `downloader.py` fetches the structure.
2.  `content_scraper.py` gets the HTML for each unit.
3.  `image_handler.py` downloads images locally.
4.  `pdf_formatter.py` constructs a single HTML file with local image references.
5.  **Playwright** opens this local HTML and prints it to PDF.

## Known Issues / Context
- **Image Downloads**: Sometimes fail due to rate limiting or network issues.
- **Playwright**: Requires `playwright install chromium` to function.
- **Windows**: `cairosvg` requires GTK3 to be in the PATH.

## Credits
Architected by the author, implemented by AI agents (Claude Sonnet, Codex, Gemini).
