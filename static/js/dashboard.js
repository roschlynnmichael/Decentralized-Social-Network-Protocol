document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const chatList = document.getElementById('chatList');
    const messageArea = document.getElementById('messageArea');
    const messageForm = document.getElementById('messageForm');
    const messageInput = document.getElementById('messageInput');
    const chatArea = document.getElementById('chatArea');
    const currentChatName = document.getElementById('currentChatName');
    const searchFriendsBtn = document.getElementById('searchFriendsBtn');
    const searchFriendsModal = new bootstrap.Modal(document.getElementById('searchFriendsModal'));
    const friendEmailSearch = document.getElementById('friendEmailSearch');
    const searchResults = document.getElementById('searchResults');
    const logoutBtn = document.getElementById('logoutBtn');

    let currentChatId = null;

    // Socket event listeners
    socket.on('connect', () => {
        console.log('Connected to server');
        fetchUserChats();
    });

    socket.on('new_message', (data) => {
        if (data.chat_id === currentChatId) {
            appendMessage(data.sender, data.content);
        }
        updateChatPreview(data.chat_id, data.content);
    });

    // Event listeners
    messageForm.addEventListener('submit', (e) => {
        e.preventDefault();
        if (messageInput.value && currentChatId) {
            sendMessage(currentChatId, messageInput.value);
            messageInput.value = '';
        }
    });

    searchFriendsBtn.addEventListener('click', () => {
        searchFriendsModal.show();
    });

    friendEmailSearch.addEventListener('input', debounce(() => {
        searchFriends(friendEmailSearch.value);
    }, 300));

    logoutBtn.addEventListener('click', () => {
        window.location.href = '/logout';
    });

    // Helper functions
    function appendMessage(sender, message) {
        const messageElement = document.createElement('p');
        messageElement.textContent = `${sender}: ${message}`;
        messageArea.appendChild(messageElement);
        messageArea.scrollTop = messageArea.scrollHeight;
    }

    function addChatToList(chatId, name, lastMessage) {
        const li = document.createElement('li');
        li.className = 'nav-item';
        li.innerHTML = `
            <a class="nav-link" href="#" data-chat-id="${chatId}">
                <span class="d-flex align-items-center">
                    <span class="flex-grow-1">${name}</span>
                    <small class="text-muted">${lastMessage}</small>
                </span>
            </a>
        `;
        li.querySelector('a').addEventListener('click', (e) => {
            e.preventDefault();
            openChat(chatId, name);
        });
        chatList.appendChild(li);
    }

    function openChat(chatId, name) {
        currentChatId = chatId;
        currentChatName.textContent = name;
        chatArea.classList.remove('d-none');
        messageArea.innerHTML = '';
        fetchChatHistory(chatId);
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // IPFS-related functions
    function fetchUserChats() {
        fetch('/api/chats')
            .then(response => response.json())
            .then(chats => {
                chatList.innerHTML = '';
                chats.forEach(chat => {
                    addChatToList(chat.id, `Chat ${chat.id}`, chat.last_message || 'No messages yet');
                });
            });
    }

    function fetchChatHistory(chatId) {
        fetch(`/api/chat/${chatId}/messages`)
            .then(response => response.json())
            .then(messages => {
                messageArea.innerHTML = '';
                messages.forEach(msg => appendMessage(msg.sender, msg.content));
            });
    }

    function sendMessage(chatId, content) {
        fetch('/api/send_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                chat_id: chatId,
                content: content
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                appendMessage('You', content);
            }
        });
    }

    function updateChatPreview(chatId, lastMessage) {
        const chatLink = chatList.querySelector(`[data-chat-id="${chatId}"]`);
        if (chatLink) {
            const previewElement = chatLink.querySelector('small');
            previewElement.textContent = lastMessage;
        }
    }

    function searchFriends(query) {
        fetch(`/api/search_friends?query=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(results => {
                searchResults.innerHTML = '';
                results.forEach(user => {
                    const userElement = document.createElement('div');
                    userElement.className = 'search-result';
                    userElement.textContent = user.username;
                    userElement.addEventListener('click', () => startChat(user.id));
                    searchResults.appendChild(userElement);
                });
            });
    }

    function startChat(userId) {
        fetch('/api/start_chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ user_id: userId }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                searchFriendsModal.hide();
                addChatToList(data.chat_id, data.chat_name, 'New chat');
                openChat(data.chat_id, data.chat_name);
            }
        });
    }
});
