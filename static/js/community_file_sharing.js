class CommunityFileSharing {
    constructor(socket) {
        this.socket = socket;
        this.downloadQueue = new Map();
        
        // Wait for DOM to be fully loaded before initializing UI
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initializeUI());
        } else {
            this.initializeUI();
        }
        
        this.setupMessageListener();
    }

    initializeUI() {
        const messageForm = document.getElementById('messageForm');
        if (!messageForm) {
            console.warn('Message form not found');
            return;
        }

        // Create file input container if it doesn't exist
        let fileInputContainer = document.getElementById('fileInputContainer');
        if (!fileInputContainer) {
            fileInputContainer = document.createElement('div');
            fileInputContainer.id = 'fileInputContainer';
            messageForm.insertBefore(fileInputContainer, messageForm.firstChild);
        }

        // Initialize file button and input if they don't exist
        const fileButton = document.getElementById('fileButton');
        const fileInput = document.getElementById('communityFileInput');

        if (fileButton && fileInput) {
            fileButton.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }

        this.setupMessageListener();
    }

    async handleFileSelect(e) {
        const files = e.target.files;
        if (!files.length || !currentCommunityId) return;

        try {
            for (const file of files) {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('community_id', currentCommunityId);

                // Show upload status
                this.showUploadStatus(file.name, 0);

                const response = await fetch('/api/community/share_file', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) throw new Error('Upload failed');
                const result = await response.json();

                // Update upload status
                this.showUploadStatus(file.name, 100);
                setTimeout(() => this.removeUploadStatus(file.name), 2000);
            }
        } catch (error) {
            console.error('Error uploading files:', error);
            alert('Failed to upload file(s)');
        }

        // Clear the input
        e.target.value = '';
    }

    showUploadStatus(filename, progress) {
        let statusContainer = document.getElementById('uploadStatusContainer');
        if (!statusContainer) {
            statusContainer = document.createElement('div');
            statusContainer.id = 'uploadStatusContainer';
            statusContainer.className = 'fixed bottom-4 right-4 space-y-2 z-50';
            document.body.appendChild(statusContainer);
        }

        let statusElement = document.getElementById(`upload-${filename}`);
        if (!statusElement) {
            statusElement = document.createElement('div');
            statusElement.id = `upload-${filename}`;
            statusElement.className = 'bg-white shadow-lg rounded-lg p-4 mb-2';
            statusElement.innerHTML = `
                <div class="flex items-center justify-between mb-2">
                    <span class="text-sm font-medium text-gray-700">Uploading: ${filename}</span>
                </div>
                <div class="h-2 bg-gray-200 rounded-full">
                    <div class="h-full bg-blue-600 rounded-full transition-all duration-300" style="width: ${progress}%"></div>
                </div>
            `;
            statusContainer.appendChild(statusElement);
        } else {
            const progressBar = statusElement.querySelector('.bg-blue-600');
            if (progressBar) progressBar.style.width = `${progress}%`;
        }
    }

    removeUploadStatus(filename) {
        const element = document.getElementById(`upload-${filename}`);
        if (element) element.remove();
    }

    handleFileDownload(fileHash, fileName, communityId) {
        // Validate parameters
        if (!fileHash || !fileName || !communityId) {
            console.error('Missing required parameters:', { fileHash, fileName, communityId });
            return;
        }

        // Create download URL with query parameter
        const downloadUrl = `/api/community/download_file/${encodeURIComponent(fileHash)}/${encodeURIComponent(fileName)}?community_id=${communityId}`;
        
        // Debug log
        console.log('Download URL:', downloadUrl);

        // Use fetch API for better error handling
        fetch(downloadUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.blob();
            })
            .then(blob => {
                // Create a download link
                const url = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = fileName;
                document.body.appendChild(link);
                link.click();
                
                // Clean up
                setTimeout(() => {
                    document.body.removeChild(link);
                    window.URL.revokeObjectURL(url);
                }, 100);
            })
            .catch(error => {
                console.error('Download error:', error);
                alert('Failed to download file. Please try again.');
            });
    }

    setupMessageListener() {
        this.socket.on('message', (message) => {
            if (message.fileInfo) {
                const messageElement = document.querySelector(`[data-message-id="${message.id}"]`);
                if (messageElement) {
                    const fileLink = messageElement.querySelector('.file-link');
                    if (fileLink) {
                        fileLink.addEventListener('click', (e) => {
                            e.preventDefault();
                            const fileHash = message.fileInfo.hash;
                            const fileName = message.fileInfo.name;
                            // Debug log
                            console.log('File info:', { fileHash, fileName, communityId: currentCommunityId });
                            if (!fileHash) {
                                console.error('File hash is missing:', message.fileInfo);
                                return;
                            }
                            this.handleFileDownload(fileHash, fileName, currentCommunityId);
                        });
                    }
                }
            }
        });
    }
}