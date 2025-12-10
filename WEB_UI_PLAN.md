# Web UI Implementation Plan

## Goal
Create a user-friendly local web interface for `mslearn-downloader` to facilitate searching, selecting, and downloading learning materials from Microsoft Learn.

## Technology Stack
- **Backend**: Python with **Flask** (lightweight, easy integration with existing code).
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla).
- **Styling**: Bootstrap 5 (for quick, responsive, and clean UI).
- **Communication**: REST API (JSON).

## Features
1.  **Search**: Search the MS Learn Catalog (Learning Paths, Courses, Modules).
2.  **Results Display**:
    - Show all results (no hidden limits).
    - Columns: Type, Title, Duration, Link (to view online).
    - Selection: Checkboxes for individual items + "Select All" toggle.
3.  **Download**:
    - Download selected items to the local `downloads/` folder.
    - "Nice graphic" for waiting/progress.
4.  **Local Execution**: Runs locally, not a public service.

## Architecture

### 1. Backend (`web_app.py`)
- **Routes**:
    - `GET /`: Serve the main SPA (Single Page Application).
    - `GET /api/search?q=<query>`: Search endpoint. Returns JSON list of results.
    - `POST /api/download`: Trigger download for selected UIDs. Returns a `job_id`.
    - `GET /api/status/<job_id>`: Poll for progress of a download job.
- **Integration**:
    - Reuse `MSLearnAPIClient` for search.
    - Reuse `MSLearnDownloader` for downloading.
    - **Challenge**: `MSLearnDownloader` currently prints to console.
    - **Solution**: Subclass or wrap `MSLearnDownloader` to emit status updates to a shared dictionary/queue that the `/api/status` endpoint can read.

### 2. Frontend
- **`templates/index.html`**: Main layout.
- **`static/css/style.css`**: Custom styles (animations for the "waiting graphic").
- **`static/js/app.js`**:
    - Handle search form submission.
    - Render results table.
    - Handle selection logic.
    - Send download request.
    - Poll for status and update the "waiting graphic".

## Implementation Steps

### Phase 1: Setup & Search
1.  Create `web_app.py` with Flask setup.
2.  Implement `/api/search` using `MSLearnAPIClient`.
3.  Create `index.html` with a search bar and results table.
4.  Add "View on MS Learn" links (construct URL from UID or use API data).

### Phase 2: Download Mechanism
1.  Create a `JobManager` to handle background download threads.
2.  Implement `/api/download` to start a thread.
3.  Implement `/api/status` to report progress (e.g., "Processing 1/5...", "Downloading images...", "Generating PDF...").
4.  Modify/Extend `MSLearnDownloader` to accept a `progress_callback`.

### Phase 3: UI Polish
1.  Add a "Select All" checkbox.
2.  Add a "Download Selected" button (floating or fixed).
3.  Create a modal or overlay with the "nice graphic" (e.g., a spinning book, filling bar) during download.
4.  Show success/error notifications.

## Directory Structure
```
f:\mslearn\
├── web_app.py              # New Flask App
├── templates/
│   └── index.html          # Main UI
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── mslearn_downloader/     # Existing package
│   └── ...
└── ...
```

## Notes
- The "only 20 items shown" issue in CLI will be naturally resolved by the Web UI rendering all items returned by the API.
- Downloads will be saved to the configured `downloads/` directory.
