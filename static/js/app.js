document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    const searchInput = document.getElementById('searchInput');
    const resultsSection = document.getElementById('resultsSection');
    const resultsBody = document.getElementById('resultsBody');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const selectAllCheckbox = document.getElementById('selectAll');
    const downloadBtn = document.getElementById('downloadBtn');
    const selectedCountSpan = document.getElementById('selectedCount');
    const resultsCountHeader = document.getElementById('resultsCount');
    
    let currentResults = [];
    let downloadModal;

    // Initialize Modal
    downloadModal = new bootstrap.Modal(document.getElementById('downloadModal'));

    // Search Handler
    searchForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const query = searchInput.value.trim();
        if (!query) return;

        // UI Reset
        resultsSection.classList.add('d-none');
        loadingSpinner.classList.remove('d-none');
        resultsBody.innerHTML = '';
        currentResults = [];
        updateSelectionState();

        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            currentResults = data;
            renderResults(data);
        } catch (error) {
            console.error('Search failed:', error);
            alert('Search failed. Please try again.');
        } finally {
            loadingSpinner.classList.add('d-none');
            resultsSection.classList.remove('d-none');
        }
    });

    // Render Table
    function renderResults(items) {
        resultsCountHeader.textContent = `Found ${items.length} results`;
        
        if (items.length === 0) {
            resultsBody.innerHTML = '<tr><td colspan="5" class="text-center py-4">No results found.</td></tr>';
            return;
        }

        items.forEach((item, index) => {
            const row = document.createElement('tr');
            
            // Determine Type Badge
            let badgeClass = 'bg-secondary';
            let typeLabel = item.type;
            if (item.type === 'learningPath') { badgeClass = 'bg-primary'; typeLabel = 'Path'; }
            else if (item.type === 'course') { badgeClass = 'bg-success'; typeLabel = 'Course'; }
            
            // Duration
            const duration = item.duration_in_minutes ? `${item.duration_in_minutes} min` : 
                             (item.duration_in_hours ? `${item.duration_in_hours} hr` : '-');

            row.innerHTML = `
                <td>
                    <input type="checkbox" class="form-check-input item-checkbox" data-index="${index}" value="${item.uid}">
                </td>
                <td><span class="badge ${badgeClass}">${typeLabel}</span></td>
                <td>
                    <div class="fw-bold">${item.title}</div>
                    <small class="text-muted">${item.uid}</small>
                </td>
                <td>${duration}</td>
                <td>
                    <a href="${item.url}" target="_blank" class="btn btn-sm btn-outline-secondary" title="View on MS Learn">
                        <i class="fas fa-external-link-alt"></i>
                    </a>
                </td>
            `;
            resultsBody.appendChild(row);
        });

        // Re-attach event listeners for checkboxes
        document.querySelectorAll('.item-checkbox').forEach(cb => {
            cb.addEventListener('change', updateSelectionState);
        });
    }

    // Select All Handler
    selectAllCheckbox.addEventListener('change', function() {
        const checkboxes = document.querySelectorAll('.item-checkbox');
        checkboxes.forEach(cb => cb.checked = this.checked);
        updateSelectionState();
    });

    // Update Selection UI
    function updateSelectionState() {
        const selected = document.querySelectorAll('.item-checkbox:checked');
        const count = selected.length;
        selectedCountSpan.textContent = count;
        downloadBtn.disabled = count === 0;
        
        // Update "Select All" state
        const allCheckboxes = document.querySelectorAll('.item-checkbox');
        if (allCheckboxes.length > 0) {
            selectAllCheckbox.checked = selected.length === allCheckboxes.length;
            selectAllCheckbox.indeterminate = selected.length > 0 && selected.length < allCheckboxes.length;
        }
    }

    // Download Handler - Open Modal
    downloadBtn.addEventListener('click', function() {
        const selectedCheckboxes = document.querySelectorAll('.item-checkbox:checked');
        if (selectedCheckboxes.length === 0) return;

        // Pre-fill folder name with search term or first item title
        const searchTerm = searchInput.value.trim();
        const safeName = searchTerm.replace(/[^a-zA-Z0-9]/g, '_');
        document.getElementById('downloadPathInput').value = safeName || 'download';

        // Reset UI
        document.getElementById('downloadConfigStep').classList.remove('d-none');
        document.getElementById('downloadProgressStep').classList.add('d-none');
        document.getElementById('downloadFooter').classList.add('d-none');
        
        downloadModal.show();
    });

    // Start Download Handler
    document.getElementById('startDownloadBtn').addEventListener('click', async function() {
        const selectedCheckboxes = document.querySelectorAll('.item-checkbox:checked');
        const itemsToDownload = Array.from(selectedCheckboxes).map(cb => {
            const index = cb.dataset.index;
            return currentResults[index];
        });

        const folderName = document.getElementById('downloadPathInput').value.trim() || 'download';
        const outputFormat = document.getElementById('outputFormatSelect').value;
        const deleteImages = document.getElementById('deleteImagesCheck').checked;

        // Switch to progress view
        document.getElementById('downloadConfigStep').classList.add('d-none');
        document.getElementById('downloadProgressStep').classList.remove('d-none');
        resetModal();

        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    items: itemsToDownload,
                    folder_name: folderName,
                    output_format: outputFormat,
                    delete_images: deleteImages
                })
            });
            
            const data = await response.json();
            if (data.job_id) {
                pollStatus(data.job_id);
            } else {
                throw new Error(data.error || 'Failed to start download');
            }
        } catch (error) {
            console.error('Download start failed:', error);
            document.getElementById('downloadStatus').textContent = 'Error';
            document.getElementById('downloadMessage').textContent = error.message;
            document.getElementById('downloadFooter').classList.remove('d-none');
        }
    });

    // Poll Status
    async function pollStatus(jobId) {
        const statusEl = document.getElementById('downloadStatus');
        const messageEl = document.getElementById('downloadMessage');
        const progressBar = document.getElementById('progressBar');
        const footer = document.getElementById('downloadFooter');

        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/api/status/${jobId}`);
                const job = await response.json();

                statusEl.textContent = job.status === 'running' ? 'Downloading...' : 
                                       (job.status === 'completed' ? 'Completed!' : 'Failed');
                messageEl.textContent = job.message;
                progressBar.style.width = `${job.progress}%`;

                if (job.status === 'completed' || job.status === 'failed') {
                    clearInterval(interval);
                    progressBar.classList.remove('progress-bar-animated');
                    if (job.status === 'completed') {
                        progressBar.classList.add('bg-success');
                    } else {
                        progressBar.classList.add('bg-danger');
                    }
                    footer.classList.remove('d-none');
                }
            } catch (error) {
                console.error('Status poll failed:', error);
                clearInterval(interval);
            }
        }, 1000);
    }

    function resetModal() {
        document.getElementById('downloadStatus').textContent = 'Starting...';
        document.getElementById('downloadMessage').textContent = 'Initializing...';
        const progressBar = document.getElementById('progressBar');
        progressBar.style.width = '0%';
        progressBar.classList.add('progress-bar-animated');
        progressBar.classList.remove('bg-success', 'bg-danger');
        document.getElementById('downloadFooter').classList.add('d-none');
    }
});
