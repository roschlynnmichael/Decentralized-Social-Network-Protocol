document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    let currentBucketHash = null;

    // DOM Elements
    const noBucketWarning = document.getElementById('noBucketWarning');
    const mainArea = document.getElementById('mainArea');
    const bucketHashElement = document.getElementById('bucketHash');
    const fileInput = document.getElementById('fileInput');
    const myFilesList = document.getElementById('myFilesList');
    const dropZone = document.querySelector('.border-dashed');
    const createBucketBtn = document.getElementById('createBucket');

    // Show/Hide UI sections
    function showMainArea(bucketHash) {
        noBucketWarning.style.display = 'none';
        mainArea.style.display = 'grid';
        bucketHashElement.textContent = bucketHash;
        currentBucketHash = bucketHash;
    }

    function showBucketWarning() {
        noBucketWarning.style.display = 'block';
        mainArea.style.display = 'none';
        bucketHashElement.textContent = 'No bucket';
        currentBucketHash = null;
    }

    // Bucket Creation
    createBucketBtn?.addEventListener('click', () => {
        createBucketBtn.disabled = true;
        createBucketBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Creating...';
        socket.emit('create_bucket');
    });

    // Socket event handlers
    socket.on('connect', () => {
        console.log('Socket connected, checking bucket status');
        socket.emit('check_bucket');
    });

    socket.on('bucket_status', (data) => {
        console.log('Received bucket status:', data);
        if (data.has_bucket) {
            showMainArea(data.bucket_hash);
            loadMyFiles();
        } else {
            showBucketWarning();
        }
    });

    // File Upload Handling
    fileInput.addEventListener('change', handleFileUpload);

    function handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Check file size (10MB limit)
        if (file.size > 10 * 1024 * 1024) {
            alert('File size exceeds 10MB limit');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        // Show upload progress in files list
        const tempFileElement = createFileElement({
            id: 'uploading',
            name: file.name,
            status: 'Uploading...',
            timestamp: Date.now() / 1000
        });
        myFilesList.insertBefore(tempFileElement, myFilesList.firstChild);

        // Upload file
        fetch('/api/share_file', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove temporary upload element
                document.getElementById('uploading')?.remove();
                // Refresh file list
                loadMyFiles();
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        })
        .catch(error => {
            console.error('Upload error:', error);
            alert('Upload failed: ' + error.message);
            document.getElementById('uploading')?.remove();
        });
    }

    function loadMyFiles() {
        socket.emit('get_my_files');
    }

    socket.on('my_files_list', (data) => {
        myFilesList.innerHTML = '';
        data.files.forEach(file => {
            const fileElement = createFileElement(file);
            myFilesList.appendChild(fileElement);
        });
    });

    function createFileElement(file) {
        const div = document.createElement('div');
        div.className = 'bg-white p-4 rounded-lg shadow flex items-center justify-between space-x-4';
        
        // Left side with file info
        const fileInfo = document.createElement('div');
        fileInfo.className = 'flex-1 min-w-0'; // Enable text truncation
        
        // Filename with truncation
        const fileName = document.createElement('p');
        fileName.className = 'text-sm font-medium text-gray-900 truncate';
        fileName.title = file.name; // Show full filename on hover
        fileName.textContent = file.name;
        
        // Status/Time info
        const fileDetails = document.createElement('p');
        fileDetails.className = 'text-sm text-gray-500';
        if (file.status) {
            fileDetails.textContent = file.status;
        } else {
            const date = new Date(file.timestamp * 1000);
            fileDetails.textContent = date.toLocaleString();
        }
        
        fileInfo.appendChild(fileName);
        fileInfo.appendChild(fileDetails);
        
        // Right side with actions
        const actions = document.createElement('div');
        actions.className = 'flex-shrink-0 flex items-center space-x-2';
        
        // Download button
        if (!file.status) { // Only show for completed uploads
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'text-blue-600 hover:text-blue-800';
            downloadBtn.innerHTML = '<i class="fas fa-download"></i>';
            downloadBtn.onclick = () => {
                // Create a temporary anchor element
                const link = document.createElement('a');
                link.href = `/api/share_file/${file.id}/${encodeURIComponent(file.name)}`;
                link.download = file.name;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            };
            actions.appendChild(downloadBtn);
            
            // Delete button
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'text-red-600 hover:text-red-800';
            deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
            deleteBtn.onclick = () => window.deleteFile(file.id);
            actions.appendChild(deleteBtn);
        }
        
        div.appendChild(fileInfo);
        div.appendChild(actions);
        
        return div;
    }

    // Drag and drop handling
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    dropZone.addEventListener('drop', handleDrop, false);

    function highlight(e) {
        dropZone.classList.add('border-blue-500', 'bg-blue-50');
    }

    function unhighlight(e) {
        dropZone.classList.remove('border-blue-500', 'bg-blue-50');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        fileInput.files = dt.files;
        handleFileUpload({ target: { files: dt.files } });
    }

    // Global functions
    window.deleteFile = function(fileId) {
        if (confirm('Are you sure you want to delete this file?')) {
            socket.emit('delete_file', { fileId });
        }
    };
});