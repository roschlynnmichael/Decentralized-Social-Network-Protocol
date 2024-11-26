document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    let currentBucketHash = null;
    let p2pChat = null;
    let currentUserId = null;
    let currentUsername = null;

    // DOM Elements
    const noBucketWarning = document.getElementById('noBucketWarning');
    const mainArea = document.getElementById('mainArea');
    const bucketHashElement = document.getElementById('bucketHash');
    const fileInput = document.getElementById('fileInput');
    const myFilesList = document.getElementById('myFilesList');
    const dropZone = document.querySelector('.border-dashed');
    const createBucketBtn = document.getElementById('createBucket');
    const messageInput = document.getElementById('messageInput');
    const sendMessageBtn = document.getElementById('sendMessageBtn');
    const chatMessages = document.getElementById('chatMessages');

    // P2P Chat Class
    class P2PChat {
        constructor(socket) {
            this.socket = socket;
            this.peers = new Map();
            this.messageInput = messageInput;
            this.sendMessageBtn = sendMessageBtn;
            this.chatMessages = chatMessages;
            
            this.initializeSocketHandlers();
            this.initializeUIHandlers();

            // Add a Set to track processed messages
            this.processedMessages = new Set();

            // Add handler for chat history cleared event
            this.socket.on('chat_history_cleared', (data) => {
                if (data.success) {
                    this.chatMessages.innerHTML = '';
                    this.processedMessages.clear();
                }
            });
        }

        initializeSocketHandlers() {
            this.socket.on('new_peer', async ({ peer_id, initiator }) => {
                await this.connectToPeer(peer_id, initiator);
            });

            this.socket.on('signal', async ({ peer_id, signal }) => {
                const peer = this.peers.get(peer_id);
                if (peer) {
                    await peer.signal(signal);
                }
            });

            this.socket.on('chat_history', (data) => {
                this.displayChatHistory(data.messages);
            });

            this.socket.on('peer_disconnected', ({ peer_id }) => {
                if (this.peers.has(peer_id)) {
                    this.peers.get(peer_id).destroy();
                    this.peers.delete(peer_id);
                }
            });
        }

        initializeUIHandlers() {
            this.sendMessageBtn.addEventListener('click', () => this.sendMessage());
            this.messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        async sendMessage() {
            const content = this.messageInput.value.trim();
            if (!content) return;

            // Remove the local display since we'll get it back from the server
            this.socket.emit('store_message', { 
                message: {
                    content: content
                }
            });

            // Clear input
            this.messageInput.value = '';
        }

        displayMessage(message, animate = false) {
            // Check if message has already been processed
            if (this.processedMessages.has(message.id)) {
                return;
            }
            this.processedMessages.add(message.id);

            const messageDiv = document.createElement('div');
            messageDiv.className = `flex ${message.sender_id === currentUserId ? 'justify-end' : 'justify-start'} ${animate ? 'message-animate-in' : ''}`;

            messageDiv.innerHTML = `
                <div class="max-w-[70%] ${message.sender_id === currentUserId ? 'bg-blue-500 text-white' : 'bg-gray-100'} 
                    rounded-lg px-4 py-2 transition-all duration-300">
                    <div class="text-xs ${message.sender_id === currentUserId ? 'text-blue-100' : 'text-gray-500'} mb-1">
                        ${message.username}
                    </div>
                    <div class="break-words">
                        ${this.escapeHtml(message.content)}
                    </div>
                    <div class="text-xs ${message.sender_id === currentUserId ? 'text-blue-100' : 'text-gray-500'} mt-1">
                        ${new Date(message.timestamp * 1000).toLocaleTimeString()}
                    </div>
                </div>
            `;

            this.chatMessages.appendChild(messageDiv);
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }

        displayChatHistory(messages) {
            this.chatMessages.innerHTML = '';
            messages.forEach(message => this.displayMessage(message));
        }

        async connectToPeer(peerId, initiator) {
            if (this.peers.has(peerId)) return;

            const peer = new SimplePeer({
                initiator,
                trickle: false
            });

            peer.on('signal', data => {
                this.socket.emit('signal', { peer_id: peerId, signal: data });
            });

            peer.on('data', data => {
                try {
                    const message = JSON.parse(data);
                    this.displayMessage(message, true);
                } catch (e) {
                    console.error('Error processing peer message:', e);
                }
            });

            this.peers.set(peerId, peer);
        }

        // Add method to clear chat history
        clearChatHistory() {
            // Check if there are any messages to clear
            if (this.chatMessages.children.length === 0) {
                console.log('Chat history is already empty');
                return;
            }

            if (confirm('Are you sure you want to clear your chat history?')) {
                this.socket.emit('clear_chat_history');
            }
        }

        // Add this helper method to escape HTML and prevent XSS
        escapeHtml(unsafe) {
            return unsafe
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }
    }

    // Show/Hide UI sections
    function showMainArea(bucketHash) {
        noBucketWarning.style.display = 'none';
        mainArea.style.display = 'grid';
        bucketHashElement.textContent = bucketHash;
        currentBucketHash = bucketHash;
        
        // Initialize P2P chat if we have user info
        if (!p2pChat && currentUserId && currentUsername) {
            p2pChat = new P2PChat(socket);
        }
    }

    function showBucketWarning() {
        noBucketWarning.style.display = 'block';
        mainArea.style.display = 'none';
        bucketHashElement.textContent = 'No bucket';
        currentBucketHash = null;
    }

    // Socket event handlers
    socket.on('connect', () => {
        console.log('Connected to server');
        socket.emit('get_user_info');
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

    socket.on('user_info', (data) => {
        currentUserId = data.user_id;
        currentUsername = data.username;
        console.log('User info received:', data);
        
        // Initialize chat if bucket is already ready
        if (currentBucketHash && !p2pChat) {
            p2pChat = new P2PChat(socket);
            
            // Add clear chat button handler
            const clearChatBtn = document.getElementById('clearChatBtn');
            clearChatBtn.addEventListener('click', () => p2pChat.clearChatHistory());
        }
    });

    socket.on('chat_message', (data) => {
        if (p2pChat) {
            p2pChat.displayMessage(data.message, true);
        }
    });

    // Bucket Creation
    createBucketBtn?.addEventListener('click', () => {
        createBucketBtn.disabled = true;
        createBucketBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Creating...';
        socket.emit('create_bucket');
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
        div.className = 'bg-white p-3 rounded-lg shadow flex items-center justify-between space-x-4 min-h-[60px]';
        
        // Left side with file info
        const fileInfo = document.createElement('div');
        fileInfo.className = 'flex-1 min-w-0'; // Enable text truncation
        
        // Filename with truncation
        const fileName = document.createElement('p');
        fileName.className = 'text-sm font-medium text-gray-900 truncate';
        fileName.title = file.name; // Show full filename on hover
        fileName.textContent = file.name;
        
        // File size/time info
        const fileDetails = document.createElement('p');
        fileDetails.className = 'text-xs text-gray-500 truncate';
        
        // Handle uploading status differently
        if (file.status === 'Uploading...') {
            fileDetails.textContent = 'Uploading...';
            div.classList.add('opacity-75');
        } else {
            fileDetails.textContent = formatFileSize(file.size || 0);
        }
        
        fileInfo.appendChild(fileName);
        fileInfo.appendChild(fileDetails);
        
        // Right side with actions
        const actions = document.createElement('div');
        actions.className = 'flex items-center space-x-2 flex-shrink-0';
        
        // Only show actions if file is not uploading
        if (!file.status) {
            // Download button
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'text-blue-600 hover:text-blue-800';
            downloadBtn.innerHTML = '<i class="fas fa-download"></i>';
            downloadBtn.onclick = () => {
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
        } else {
            // Show spinner for uploading files
            const spinner = document.createElement('div');
            spinner.className = 'text-blue-500';
            spinner.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            actions.appendChild(spinner);
        }
        
        div.appendChild(fileInfo);
        div.appendChild(actions);
        
        return div;
    }

    // Helper function to format file size
    function formatFileSize(bytes) {
        if (!bytes || isNaN(bytes)) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
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

    socket.on('error', (data) => {
        console.error('Socket error:', data.message);
        if (data.message === 'Please log in to continue') {
            // Redirect to login page
            window.location.href = '/login';
        }
    });
});