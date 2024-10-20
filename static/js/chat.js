var currentChatFriendId = null;
var socket = io('/');  // Connect to the default namespace

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

function setupFileSharing() {
    const fileInput = document.getElementById('fileInput');
    const shareFileBtn = document.getElementById('shareFileBtn');

    shareFileBtn.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            shareFile(file);
        }
    });
}

function shareFile(file) {
    const maxSize = 100 * 1024 * 1024; // 100 MB
    if (file.size > maxSize) {
        alert(`File is too large. Maximum file size is ${maxSize / (1024 * 1024)} MB.`);
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    fetch('/api/share_file', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { throw err; });
        }
        return response.json();
    })
    .then(data => {
        if (data.file_link) {
            const message = `Shared file: [Download](${data.file_link})`;
            sendMessage(currentChatFriendId, message);
        } else {
            throw new Error('Unexpected response from server');
        }
    })
    .catch(error => {
        console.error('Error sharing file:', error);
        alert(error.error || 'An error occurred while sharing the file. Please try again.');
    });
}

function renderMessage(senderId, content, timestamp) {
    const messageArea = document.getElementById('messageArea');
    const messageElement = document.createElement('div');
    messageElement.className = 'message';
    
    const senderLabel = senderId === currentUserId ? 'You' : 'Friend';
    const localTimestamp = new Date(timestamp).toLocaleString();
    
    // Replace download links with actual clickable links
    content = content.replace(/Shared file: \[Download\]\((.*?)\)/g, (match, p1) => {
        const fileName = p1.split('/').pop();
        return `Shared file: <a href="${p1}" download="${fileName}" target="_blank">Download ${fileName}</a>`;
    });

    messageElement.innerHTML = `
        <strong>${senderLabel}</strong>: ${content}
        <small class="text-muted">${localTimestamp}</small>
    `;
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

    socket.emit('join', { room: `chat_${Math.min(currentUserId, friendId)}_${Math.max(currentUserId, friendId)}` });

    socket.on('new_message', (data) => {
        console.log('Received new message:', data);
        if (data.sender_id == friendId) {
            addMessageToChat(data.sender_id, data.content, new Date(data.timestamp));
            updateChatPreview(data.sender_id, data.content);
        } else {
            console.log('Received message is not from current chat friend');
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

    // Add the message to the chat immediately for the sender
    addMessageToChat(currentUserId, message, new Date(timestamp));

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
            removeLastMessage();
        }
    })
    .catch(error => {
        console.error('Error sending message:', error);
        removeLastMessage();
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
