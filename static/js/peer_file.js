// Define socket and formatFileSize in the global scope
let socket;

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Main document ready handler
document.addEventListener('DOMContentLoaded', function() {
    // Initialize socket
    socket = io();
    
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const fileInput = document.getElementById('fileInput');
    const searchResults = document.getElementById('searchResults');
    const mySharedFiles = document.getElementById('mySharedFiles');

    // Helper Functions
    function createFileElement(file) {
        const element = document.createElement('div');
        element.className = 'flex justify-between items-center p-2 border rounded-lg';
        element.innerHTML = `
            <div class="flex-1">
                <p class="font-medium">${file.name}</p>
                <p class="text-sm text-gray-500">${formatFileSize(file.size)}</p>
                ${file.status ? `<p class="text-xs text-gray-400">${file.status}</p>` : ''}
            </div>
            <div class="flex space-x-2">
                ${file.downloadUrl ? 
                    `<a href="${file.downloadUrl}" class="text-blue-600 hover:text-blue-800">
                        <i class="fas fa-download"></i>
                    </a>` : ''}
                <button onclick="deleteFile('${file.id}')" class="text-red-600 hover:text-red-800">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        return element;
    }

    function loadMySharedFiles() {
        fetch('/api/my_shared_files')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const filesList = document.getElementById('mySharedFiles');
                    if (!filesList) return;

                    filesList.innerHTML = '';
                    data.files.forEach(file => {
                        const element = document.createElement('div');
                        element.className = 'flex justify-between items-center p-2 border rounded-lg mb-2';
                        element.innerHTML = `
                            <div class="flex-1">
                                <p class="font-medium">${file.name}</p>
                                <p class="text-xs text-gray-400">${formatFileSize(file.size)}</p>
                            </div>
                            <div class="flex space-x-2">
                                <button onclick="downloadFile('${file.id}', '${file.name}')" 
                                        class="text-blue-600 hover:text-blue-800">
                                    <i class="fas fa-download"></i>
                                </button>
                                <button onclick="deleteFile('${file.id}')" 
                                        class="text-red-600 hover:text-red-800">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        `;
                        filesList.appendChild(element);
                    });
                }
            })
            .catch(error => console.error('Error loading shared files:', error));
    }

    // File Upload Handler
    fileInput.addEventListener('change', async function(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Check file size
        if (file.size > 10 * 1024 * 1024) {
            alert('File size exceeds 10MB limit');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            // Show upload progress
            const tempElement = createFileElement({
                name: file.name,
                size: file.size,
                status: 'Uploading...'
            });
            mySharedFiles.insertBefore(tempElement, mySharedFiles.firstChild);

            // Share file with P2P network
            socket.emit('share_p2p_file', {
                filename: file.name,
                size: file.size
            });

            // Upload to server
            const response = await fetch('/api/share_file', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.success) {
                loadMySharedFiles();
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            alert('Upload failed: ' + error.message);
        }
    });

    // Search Handler
    searchBtn.addEventListener('click', function() {
        const searchTerm = searchInput.value.trim();
        if (!searchTerm) return;

        searchResults.innerHTML = '<div class="text-center text-gray-500 p-4">Searching...</div>';
        
        // Emit search event with unique ID
        socket.emit('search_files', {
            query: searchTerm,
            id: `search_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
        });
    });

    // Socket Listeners
    socket.on('search_results', function(data) {
        console.log('Search results received:', data); // Debug log
        if (data.success) {
            displaySearchResults(data.results);
        } else {
            console.error('Search error:', data.error);
            searchResults.innerHTML = `<div class="text-center text-red-500 p-4">Search failed: ${data.error}</div>`;
        }
    });

    socket.on('file_shared', function(data) {
        loadMySharedFiles();
    });

    socket.on('download_progress', function(data) {
        // Update download progress if needed
        console.log('Download progress:', data);
    });

    // Initial load
    loadMySharedFiles();

    // Move the event handlers inside DOMContentLoaded
    window.deleteFile = function(fileId) {
        if (!confirm('Are you sure you want to delete this file?')) return;

        fetch(`/api/delete_file/${fileId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadMySharedFiles();
                showNotification('File deleted successfully', 'success');
            } else {
                showNotification(data.error || 'Failed to delete file', 'error');
            }
        })
        .catch(error => {
            console.error('Error deleting file:', error);
            showNotification('Failed to delete file', 'error');
        });
    };

    window.downloadFile = function(filename, source) {
        socket.emit('download_file', {
            filename: filename,
            source: source
        });
    };

    window.downloadP2PFile = function(filename, source) {
        socket.emit('p2p_request_file', {
            filename: filename,
            source: JSON.parse(source)
        });
    };

    // Move loadMySharedFiles to global scope but keep the reference
    window.loadMySharedFiles = loadMySharedFiles;
});

// Keep these utility functions in the global scope
function displaySearchResults(results) {
    const searchResults = document.getElementById('searchResults');
    if (!searchResults) return;

    searchResults.innerHTML = '';
    if (results && results.length > 0) {
        results.forEach(file => {
            const element = document.createElement('div');
            element.className = 'flex justify-between items-center p-2 border rounded-lg mb-2';
            element.innerHTML = `
                <div class="flex-1">
                    <p class="font-medium">${file.name}</p>
                    <p class="text-sm text-gray-500">From: ${file.username || 'Unknown'}</p>
                    ${file.size ? `<p class="text-xs text-gray-400">${formatFileSize(file.size)}</p>` : ''}
                </div>
                <div class="flex space-x-2">
                    <button onclick="downloadP2PFile('${file.name}', ${JSON.stringify(file.source)})" 
                            class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-1 px-3 rounded">
                        <i class="fas fa-download mr-1"></i> Download
                    </button>
                </div>
            `;
            searchResults.appendChild(element);
        });
    } else {
        searchResults.innerHTML = '<div class="text-center text-gray-500 p-4">No results found</div>';
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg ${
        type === 'success' ? 'bg-green-500' : 
        type === 'error' ? 'bg-red-500' : 
        'bg-blue-500'
    } text-white`;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}