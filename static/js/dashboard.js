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
        // TODO: Fetch user's chats and populate chatList
    });

    socket.on('new_message', (data) => {
        if (data.chat_id === currentChatId) {
            appendMessage(data.sender, data.message);
        }
        // TODO: Update chat list to show new message preview
    });

    // Event listeners
    messageForm.addEventListener('submit', (e) => {
        e.preventDefault();
        if (messageInput.value && currentChatId) {
            socket.emit('send_message', {
                chat_id: currentChatId,
                message: messageInput.value
            });
            appendMessage('You', messageInput.value);
            messageInput.value = '';
        }
    });

    searchFriendsBtn.addEventListener('click', () => {
        searchFriendsModal.show();
    });

    friendEmailSearch.addEventListener('input', debounce(() => {
        // TODO: Implement friend search functionality
        searchResults.innerHTML = '<p>Searching...</p>';
    }, 300));

    logoutBtn.addEventListener('click', () => {
        // TODO: Implement logout functionality
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
        // TODO: Fetch and display chat history
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

    // TODO: Implement functions to fetch user's chats, chat history, and search for friends
});