# MS Learn Downloader - TODO

## 🔥 Critical Priority

### 1. Retry missing units (404 set)
- [x] Re-run the missing modules/units when slugs recover:
  - `run-non-functional-tests-azure-pipelines` units 3–7
  - `manage-release-cadence` units 1–7
  - `github-actions-ci` units 1–8
  - `understand-package-management` self-hosted/SaaS sources; package management with Azure Artifacts
  - `collaborate-pull-requests-azure-repos` exercise unit
- [x] Investigate alternative slugs or archive captures for critical labs.
  - **Resolved:** Implemented robust URL resolution by parsing module pages to find exact unit URLs.

### 2. Improve image download success rate
- [ ] Add structured error logging (status codes, URL) in `download_image()`.
- [ ] Add retry with backoff and optional delay between requests.
- [ ] Consider User-Agent/referrer tweaks if 429/403 encountered.

## 📋 High Priority

### 3. PDF/image verification
- [ ] Spot-check several PDFs from the 14-path batch to confirm embedded images and layout.
- [ ] Add a lightweight validation (file exists and size > 0) post-generation.

### 4. Housekeeping
- [ ] Remove `test_playwright` once external lock is released.
- [ ] Capture batch run summary in `STATUS.md` (done) and keep in sync after future runs.

## 🔧 Medium Priority

### 5. Error handling & resilience
- [ ] Continue on failed images with better summaries at the end of runs.
- [ ] Optional: cache API responses to reduce re-fetches.

### 6. Documentation follow-ups
- [ ] Add contributing/maintenance notes if project is shared further.
- [ ] Document known 404 gaps and retry guidance.

### 7. Features
- [x] Support downloading entire courses by URL (e.g., `https://learn.microsoft.com/en-us/training/courses/pl-400t00`).

## 📝 Notes

- Content extraction and PDF image embedding are resolved (Playwright + local image paths).
- Full AZ-400 batch completed; PDFs live in `downloads/az-400/`.
