let socket;
if (!socket) {
    socket = io('/');
}

var currentChatFriendId = null;

if (typeof currentUserId == 'undefined'){
    console.error('currentUserId is not defined. Make sure it is set in HTML before the script loads!');
}

// Add this near the top of the file, after the socket initialization
document.addEventListener('DOMContentLoaded', function() {
    const clearChatButton = document.getElementById('clearChatButton');
    if (clearChatButton) {
        clearChatButton.addEventListener('click', clearChat);
    }
});

// Add this function to your chat.js file
function clearChat() {
    if (confirm('Are you sure you want to clear your chat history? This action cannot be undone and will only affect your view of the conversation.')) {
        fetch(`/api/clear_chat/${currentChatFriendId}`, {
            method: 'POST',
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('messageArea').innerHTML = '<p class="text-muted">No messages to display.</p>';
                console.log('Chat history cleared successfully');
            } else {
                console.error('Failed to clear chat history:', data.error);
            }
        })
        .catch(error => {
            console.error('Error clearing chat history:', error);
        });
    }
}

let isUploading = false;

function setupFileSharing() {
    const fileInput = document.getElementById('fileInput');
    const shareFileBtn = document.getElementById('shareFileBtn');

    // Remove any existing event listeners
    shareFileBtn.removeEventListener('click', handleShareButtonClick);
    fileInput.removeEventListener('change', handleFileSelection);

    // Add new event listeners
    shareFileBtn.addEventListener('click', handleShareButtonClick);
    fileInput.addEventListener('change', handleFileSelection);
}

function handleShareButtonClick(event) {
    event.preventDefault();
    const fileInput = document.getElementById('fileInput');
    fileInput.click();
}

function handleFileSelection(event) {
    const file = event.target.files[0];
    if (file && !isUploading) {
        shareFile(file);
    }
}

function shareFile(file) {
    if (isUploading) return;

    const maxSize = 100 * 1024 * 1024; // 100 MB
    if (file.size > maxSize) {
        alert(`File is too large. Maximum file size is ${maxSize / (1024 * 1024)} MB.`);
        return;
    }

    isUploading = true;
    const shareFileBtn = document.getElementById('shareFileBtn');
    shareFileBtn.disabled = true;

    const formData = new FormData();
    formData.append('file', file);

    fetch('/api/share_file', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const txHashInfo = data.tx_hash ? 
                `(Verified on blockchain: ${data.tx_hash})` : 
                '(Blockchain verification pending...)';
            
            const message = `Shared file: [Download](${data.file_link}) ${txHashInfo}`;
            sendMessage(currentChatFriendId, message);
            document.getElementById('fileInput').value = '';
        } else {
            throw new Error(data.error || 'Unexpected response from server');
        }
    })
    .catch(error => {
        console.error('Error sharing file:', error);
        alert('An error occurred while sharing the file. Please try again.');
    })
    .finally(() => {
        isUploading = false;
        shareFileBtn.disabled = false;
    });
}

function verifyFile(ipfsHash) {
    fetch(`/api/verify_file/${ipfsHash}`)
    .then(response => response.json())
    .then(data => {
        if (data.verified) {
            alert(`File verified. Owner: ${data.owner}`);
        } else {
            alert('File verification failed.');
        }
    })
    .catch(error => {
        console.error('Error verifying file:', error);
        alert('An error occurred while verifying the file.');
    });
}

function renderMessage(senderId, content, timestamp) {
    const messageArea = document.getElementById('messageArea');
    const messageElement = document.createElement('div');
    messageElement.className = 'message';
    
    // Determine if the message is from the current user
    const senderLabel = Number(senderId) === Number(currentUserId) ? 'You' : 'Friend';
    const localtimestamp = new Date(timestamp).toLocaleString();
    
    // Parse the decrypted content
    let messageContent = '';
    let messageType = 'text';
    
    if (typeof content === 'object') {
        messageType = content.type || 'text';
        messageContent = content.content;
    } else {
        messageContent = content;
    }

    // Create message header
    let headerHTML = `
        <div class="message-header">
            <strong>${senderLabel}</strong>
            <small class="text-muted">${localtimestamp}</small>
        </div>
    `;

    // Create message content based on type
    let contentHTML = '';
    if (messageType === 'file') {
        const fileName = messageContent.filename || messageContent.split('/').pop();
        contentHTML = `
            <div class="message-content file-message">
                <i class="fas fa-file"></i>
                <a href="${messageContent}" download="${fileName}" target="_blank">
                    Download ${fileName}
                </a>
            </div>
        `;
    } else {
        contentHTML = `
            <div class="message-content">
                ${messageContent}
            </div>
        `;
    }

    messageElement.innerHTML = headerHTML + contentHTML;
    messageArea.appendChild(messageElement);
    messageArea.scrollTop = messageArea.scrollHeight;
}

function startChat(friendId, friendName) {
    currentChatFriendId = friendId;
    console.log('Starting chat with friend:', friendId, friendName);

    const currentChatNameElement = document.getElementById('currentChatName');
    if (currentChatNameElement) {
        currentChatNameElement.textContent = friendName;
    }

    const chatArea = document.getElementById('chatArea');
    if (chatArea) {
        chatArea.classList.remove('d-none');
    }

    loadChatHistory(friendId);

    // Remove existing listeners before adding new ones
    socket.off('new_message');

    const room = `chat_${Math.min(currentUserId, friendId)}_${Math.max(currentUserId, friendId)}`;
    socket.emit('join', { room: room });

    // Create a Set to store unique message identifiers
    const receivedMessages = new Set();

    socket.on('new_message', (data) => {
        console.log('Received new message:', data);
        // Create a unique identifier for the message
        const messageId = `${data.sender_id}-${data.timestamp}`;
        
        // Check if we've already processed this message
        if (!receivedMessages.has(messageId)) {
            receivedMessages.add(messageId);
            
            addMessageToChat(data.sender_id, data.content, new Date(data.timestamp));
            updateChatPreview(data.sender_id, data.content);
        } else {
            console.log('Duplicate message received, ignoring:', messageId);
        }
    });

    // Show the clear chat button when a chat is started
    const clearChatButton = document.getElementById('clearChatButton');
    if (clearChatButton) {
        clearChatButton.classList.remove('d-none');
    }

    setupFileSharing();
}

window.sendMessage = function(friendId, message) {
    const room = `chat_${Math.min(currentUserId, friendId)}_${Math.max(currentUserId, friendId)}`;
    const timestamp = new Date().toISOString();
    
    console.log('Sending message:', { friendId, message, room, timestamp });

    fetch('/api/send_message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            friend_id: friendId,
            message: message,
            room: room,
            timestamp: timestamp
        }),
    })
    .then(response => response.json())
    .then(data => {
        console.log('Server response:', data);
        document.getElementById('messageInput').value = '';
        if (data.error) {
            console.error('Error from server:', data.error);
        }
    })
    .catch(error => {
        console.error('Error sending message:', error);
    });
};

// Modify the loadChatHistory function to handle potentially cleared chat history
function loadChatHistory(friendId) {
    fetch(`/api/chat_history/${friendId}`)
    .then(response => response.json())
    .then(data => {
        console.log('Received chat history:', data);
        const messageArea = document.getElementById('messageArea');
        messageArea.innerHTML = ''; // Clear existing messages
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => {
                renderMessage(msg.sender_id, msg.content, msg.timestamp);
            });
        } else {
            messageArea.innerHTML = '<p class="text-muted">No messages to display.</p>';
        }
        // Scroll to the bottom of the message area
        messageArea.scrollTop = messageArea.scrollHeight;
    })
    .catch(error => console.error('Error loading chat history:', error));
}

function addMessageToChat(senderId, content, timestamp) {
    console.log('Adding message to chat:', { senderId, content, timestamp });
    
    const messageArea = document.getElementById('messageArea');
    const messageElement = document.createElement('div');
    messageElement.className = 'message';
    const senderLabel = Number(senderId) === Number(currentUserId) ? 'You' : 'Friend';
    
    // Convert timestamp to local time
    const localTimestamp = new Date(timestamp).toLocaleString();
    
    // Replace download links with actual clickable links
    content = content.replace(/Shared file: \[Download\]\((.*?)\)/g, (match, p1) => {
        const fileName = p1.split('/').pop();
        return `Shared file: <a href="${p1}" download="${fileName}">Download ${fileName}</a>`;
    });

    messageElement.innerHTML = `
        <strong>${senderLabel}</strong>: ${content}
        <small class="text-muted">${localTimestamp}</small>
    `;
    messageArea.appendChild(messageElement);
    messageArea.scrollTop = messageArea.scrollHeight;
    
    console.log('Message added to chat. Current message count:', messageArea.children.length);
}

function updateChatPreview(senderId, content) {
    // Implement this function to update the chat preview in the friend list
    // This is just a placeholder and should be implemented based on your UI
    console.log('Updating chat preview:', { senderId, content });
}

// Optional: Function to remove the last message (in case of error)
function removeLastMessage() {
    const messageArea = document.getElementById('messageArea');
    if (messageArea.lastChild) {
        messageArea.removeChild(messageArea.lastChild);
        console.log('Last message removed. Current message count:', messageArea.children.length);
    }
}

// Add this to hide the clear button when no chat is active
function endChat() {
    currentChatFriendId = null;
    document.getElementById('currentChatName').textContent = '';
    document.getElementById('chatArea').classList.add('d-none');
    document.getElementById('clearChatButton').style.display = 'none';
}

document.getElementById('signChatButton').addEventListener('click', function() {
    fetch(`/api/sign_chat/${currentChatFriendId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        alert(`Chat signed. Signature: ${data.signature}`);
    })
    .catch(error => {
        console.error('Error signing chat:', error);
        alert('An error occurred while signing the chat.');
    });
});

// Add this to your existing JavaScript
function updateBlockchainStatus() {
    fetch('/api/blockchain_status')
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        const statusMessage = data.connected 
            ? `Connected to blockchain (Block: ${data.latest_block})`
            : 'Disconnected from blockchain';
        
        const statusClass = data.connected ? 'alert-success' : 'alert-danger';
        
        showBlockchainStatus(statusMessage, statusClass);
    })
    .catch(error => {
        console.error('Error fetching blockchain status:', error);
        showBlockchainStatus('Error checking blockchain status', 'alert-warning');
    });
}

function showBlockchainStatus(message, alertClass) {
    const modal = new bootstrap.Modal(document.getElementById('blockchainStatusModal'));
    const messageElement = document.getElementById('blockchainStatusMessage');
    messageElement.textContent = message;
    messageElement.className = `alert ${alertClass}`;
    modal.show();
    setTimeout(() => modal.hide(), 10000); // Show for 10 seconds
}

// Call this function immediately and then periodically
//updateBlockchainStatus();
//setInterval(updateBlockchainStatus, 30000); // Update every 30 seconds

let isConnectedToBlockchain = false;

function checkBlockchainStatus() {
    fetch('/api/blockchain_status')
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.connected && !isConnectedToBlockchain) {
            showBlockchainStatus(`Connected to blockchain (Block: ${data.latest_block})`, 'alert-success');
            isConnectedToBlockchain = true;
        } else if (!data.connected && isConnectedToBlockchain) {
            showBlockchainStatus('Disconnected from blockchain', 'alert-danger');
            isConnectedToBlockchain = false;
        }
    })
    .catch(error => {
        console.error('Error fetching blockchain status:', error);
        if (isConnectedToBlockchain) {
            showBlockchainStatus('Error checking blockchain status', 'alert-warning');
            isConnectedToBlockchain = false;
        }
    });
}

function showBlockchainStatus(message, alertClass) {
    const modal = new bootstrap.Modal(document.getElementById('blockchainStatusModal'));
    const messageElement = document.getElementById('blockchainStatusMessage');
    messageElement.textContent = message;
    messageElement.className = `alert ${alertClass}`;
    modal.show();
    setTimeout(() => modal.hide(), 10000); // Show for 10 seconds
}

// Check status initially and then every 30 seconds, but only show changes
checkBlockchainStatus();
setInterval(checkBlockchainStatus, 14400000); // Check every 4 hours (14400000 ms)

document.addEventListener('DOMContentLoaded', function() {
    const messageForm = document.getElementById('messageForm');
    if (messageForm) {
        messageForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const messageInput = document.getElementById('messageInput');
            const message = messageInput.value.trim();
            if (message && currentChatFriendId) {
                sendMessage(currentChatFriendId, message);
                messageInput.value = '';
            }
        });
    }
    setupFileSharing();
});
