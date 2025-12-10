import os
import threading
import uuid
import time
from flask import Flask, render_template, request, jsonify
from mslearn_downloader.config import Config
from mslearn_downloader.api_client import MSLearnAPIClient
from mslearn_downloader.downloader import MSLearnDownloader

app = Flask(__name__)

# Global state for jobs
jobs = {}

def get_downloader():
    config = Config()
    # Ensure we use the configured output directory or a default one
    return MSLearnDownloader(config)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    config = Config()
    api_client = MSLearnAPIClient(config)
    
    # Check if query is a URL
    if 'learn.microsoft.com' in query and ('/paths/' in query or '/courses/' in query or '/modules/' in query):
        # Try to resolve URL to a single item
        item = api_client.get_learning_path_from_url(query)
        if item:
            # Normalize item structure for frontend
            if 'uid' not in item:
                # Should have UID, but just in case
                pass
            return jsonify([item])
        else:
            # If URL resolution fails, return empty or try search?
            # Let's return empty for now if it looked like a URL but failed
            return jsonify([])

    # Reuse the search logic
    results = api_client.search_catalog(query, types=['learningPaths', 'courses', 'modules'])
    return jsonify(results)

def run_download_job(job_id, items, output_dir, output_format, delete_images):
    """Background worker for downloading items."""
    job = jobs[job_id]
    job['status'] = 'running'
    
    config = Config()
    if delete_images:
        config.set('cleanup.delete_images', True)
        
    downloader = MSLearnDownloader(config)
    
    total = len(items)
    success_count = 0
    
    try:
        for i, item in enumerate(items, 1):
            uid = item.get('uid')
            item_type = item.get('type')
            title = item.get('title')
            
            job['current_item'] = title
            job['progress'] = int((i - 1) / total * 100)
            job['message'] = f"Processing {i}/{total}: {title}"
            
            success = False
            try:
                if item_type == 'course':
                    success = downloader.download_course_by_uid(uid, output_format, output_dir)
                elif item_type == 'module':
                    success = downloader.download_module(uid, output_format, output_dir)
                else:
                    success = downloader.download_learning_path(learning_path_uid=uid, output_format=output_format, output_dir=output_dir)
            except Exception as e:
                print(f"Error downloading {uid}: {e}")
            
            if success:
                success_count += 1
                
        job['progress'] = 100
        job['status'] = 'completed'
        job['message'] = f"Completed. Successfully downloaded {success_count}/{total} items."
        
    except Exception as e:
        job['status'] = 'failed'
        job['message'] = f"Job failed: {str(e)}"

@app.route('/api/download', methods=['POST'])
def download():
    data = request.json
    items = data.get('items', [])
    folder_name = data.get('folder_name', 'download')
    output_format = data.get('output_format', 'pdf')
    delete_images = data.get('delete_images', False)
    
    if not items:
        return jsonify({'error': 'No items selected'}), 400
    
    job_id = str(uuid.uuid4())
    
    # Determine output directory
    config = Config()
    base_output_dir = config.get('storage.output_dir', './downloads')
    output_dir = os.path.join(base_output_dir, folder_name)
    
    # Create job entry
    jobs[job_id] = {
        'id': job_id,
        'status': 'queued',
        'progress': 0,
        'message': 'Starting...',
        'total_items': len(items)
    }
    
    # Start background thread
    thread = threading.Thread(target=run_download_job, args=(job_id, items, output_dir, output_format, delete_images))
    thread.start()
    
    return jsonify({'job_id': job_id})

@app.route('/api/status/<job_id>')
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)

if __name__ == '__main__':
    print("Starting MS Learn Downloader Web UI...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000)
