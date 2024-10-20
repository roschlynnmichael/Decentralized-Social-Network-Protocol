document.addEventListener('DOMContentLoaded', function() {
    const socket = io();
    const chatList = document.getElementById('chatList');
    const messageArea = document.getElementById('messageArea');
    const messageForm = document.getElementById('messageForm');
    const messageInput = document.getElementById('messageInput');
    const chatArea = document.getElementById('chatArea');
    const currentChatName = document.getElementById('currentChatName');
    const friendSearch = document.getElementById('friendSearch');
    const logoutBtn = document.getElementById('logoutBtn');
    const notificationList = document.getElementById('notificationList');
    const notificationBadge = document.getElementById('notificationBadge');
    const usernameSpan = document.getElementById('username');
    const noNotifications = document.getElementById('noNotifications');
    const friendSearchResults = document.getElementById('friendSearchResults');
    const changeProfilePic = document.getElementById('changeProfilePic');
    const removeProfilePic = document.getElementById('removeProfilePic');
    const profilePicModal = new bootstrap.Modal(document.getElementById('profilePicModal'));
    const profilePicForm = document.getElementById('profilePicForm');
    const profilePicInput = document.getElementById('profilePicInput');
    const uploadProfilePic = document.getElementById('uploadProfilePic');
    const navProfilePic = document.getElementById('navProfilePic');

    let currentChatId = null;

    // Socket event listeners
    socket.on('connect', () => {
        console.log('Connected to server');
        fetchFriends();
        loadFriendRequests();
        fetchUsername();
    });

    socket.on('new_message', (data) => {
        if (data.chat_id === currentChatId) {
            appendMessage(data.sender, data.content);
        }
        updateChatPreview(data.chat_id, data.content);
    });

    // Add this new socket event listener
    socket.on('friend_request_accepted', (data) => {
        addFriendToList(data);
    });

    // Event listeners
    messageForm.addEventListener('submit', (e) => {
        e.preventDefault();
        if (messageInput.value && currentChatId) {
            window.sendMessage(currentChatId, messageInput.value);
            // Remove this line, as we're clearing the input in the sendMessage function
            // messageInput.value = '';
        }
    });

    friendSearch.addEventListener('input', debounce(() => {
        searchFriends(friendSearch.value);
    }, 300));

    logoutBtn.addEventListener('click', () => {
        window.location.href = '/logout';
    });

    changeProfilePic.addEventListener('click', () => {
        profilePicModal.show();
    });

    removeProfilePic.addEventListener('click', () => {
        if (confirm('Are you sure you want to remove your profile picture?')) {
            fetch('/remove_profile_picture', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.message) {
                    alert(data.message);
                    updateProfilePicture('default.png');
                } else {
                    alert(data.error || 'An error occurred while removing the profile picture');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while removing the profile picture');
            });
        }
    });

    uploadProfilePic.addEventListener('click', () => {
        const file = profilePicInput.files[0];
        if (file) {
            const formData = new FormData();
            formData.append('file', file);

            fetch('/upload_profile_picture', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.filename) {
                    updateProfilePicture(data.filename);
                    profilePicModal.hide();
                    alert('Profile picture updated successfully');
                } else {
                    alert(data.error || 'An error occurred while updating the profile picture');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while updating the profile picture');
            });
        } else {
            alert('Please select a file first');
        }
    });

    function updateProfilePicture(filename) {
        const newProfilePicUrl = `/static/profile_pictures/${filename}`;
        document.querySelectorAll('img[alt="Profile"]').forEach(img => {
            img.src = newProfilePicUrl;
        });
    }

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

    function openChat(friendId, friendName) {
        currentChatId = friendId;
        startChat(friendId, friendName);
        const chatArea = document.getElementById('chatArea');
        if (chatArea) {
            chatArea.classList.remove('d-none');
        }
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

    function updateChatPreview(chatId, lastMessage) {
        const chatLink = chatList.querySelector(`[data-chat-id="${chatId}"]`);
        if (chatLink) {
            const previewElement = chatLink.querySelector('small');
            previewElement.textContent = lastMessage;
        }
    }

    function searchFriends(query) {
        if (query.length < 3) {
            friendSearchResults.innerHTML = '<li class="list-group-item">Type at least 3 characters to search</li>';
            return;
        }

        fetch(`/api/search_users?query=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(users => {
                friendSearchResults.innerHTML = '';
                if (users.length === 0) {
                    friendSearchResults.innerHTML = '<li class="list-group-item">No users found</li>';
                } else {
                    users.forEach(user => {
                        const li = document.createElement('li');
                        li.className = 'list-group-item d-flex justify-content-between align-items-center';
                        li.innerHTML = `
                            ${user.username}
                            <button class="btn btn-sm btn-primary add-friend-btn" data-user-id="${user.id}">Add Friend</button>
                        `;
                        li.querySelector('.add-friend-btn').addEventListener('click', () => sendFriendRequest(user.id));
                        friendSearchResults.appendChild(li);
                    });
                }
            })
            .catch(error => console.error('Error searching users:', error));
    }

    function sendFriendRequest(userId) {
        fetch('/api/send_friend_request', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ receiver_id: userId }),
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw err; });
            }
            return response.json();
        })
        .then(data => {
            alert(data.message);
        })
        .catch(error => {
            console.error('Error sending friend request:', error);
            alert(error.error || 'An error occurred while sending the friend request.');
        });
    }

    function loadFriendRequests() {
        fetch('/friend_requests')
        .then(response => response.json())
        .then(requests => {
            notificationList.innerHTML = ''; // Clear existing notifications
            if (requests.length === 0) {
                notificationBadge.style.display = 'none';
                notificationList.innerHTML = '<li class="dropdown-item" id="noNotifications">No notifications for today</li>';
            } else {
                notificationBadge.style.display = 'inline-block';
                notificationBadge.textContent = requests.length;
                requests.forEach(request => {
                    const li = document.createElement('li');
                    li.className = 'notification-item dropdown-item';
                    li.innerHTML = `
                        <div>${request.sender_username} wants to be your friend</div>
                        <div class="notification-buttons">
                            <button class="btn btn-sm btn-success accept-request" data-request-id="${request.id}">Accept</button>
                            <button class="btn btn-sm btn-danger reject-request" data-request-id="${request.id}">Reject</button>
                        </div>
                    `;
                    li.querySelector('.accept-request').addEventListener('click', () => acceptFriendRequest(request.id));
                    li.querySelector('.reject-request').addEventListener('click', () => rejectFriendRequest(request.id));
                    notificationList.appendChild(li);
                });
            }
        })
        .catch(error => console.error('Error loading friend requests:', error));
    }

    function acceptFriendRequest(requestId) {
        fetch(`/accept_friend_request/${requestId}`, { method: 'POST' })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw err; });
            }
            return response.json();
        })
        .then(data => {
            alert(data.message);
            loadFriendRequests(); // Reload the friend requests
            // Remove this line as we'll update the friend list via WebSocket
            // fetchFriends();
        })
        .catch(error => {
            console.error('Error:', error);
            alert(error.error || 'An error occurred while accepting the friend request.');
        });
    }

    function rejectFriendRequest(requestId) {
        fetch(`/reject_friend_request/${requestId}`, { method: 'POST' })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw err; });
            }
            return response.json();
        })
        .then(data => {
            alert(data.message);
            loadFriendRequests(); // Reload the friend requests
        })
        .catch(error => {
            console.error('Error:', error);
            alert(error.error || 'An error occurred while rejecting the friend request.');
        });
    }

    function fetchUsername() {
        fetch('/api/current_user')
        .then(response => response.json())
        .then(data => {
            usernameSpan.textContent = data.username;
        })
        .catch(error => console.error('Error fetching username:', error));
    }

    function fetchFriends() {
        fetch('/api/friends')
            .then(response => response.json())
            .then(friends => {
                chatList.innerHTML = '';
                friends.forEach(friend => {
                    addFriendToList(friend);
                });
            })
            .catch(error => console.error('Error fetching friends:', error));
    }

    function addFriendToList(friend) {
        const existingFriend = document.querySelector(`#chatList [data-friend-id="${friend.friend_id}"]`);
        if (existingFriend) {
            return; // Friend already in the list, no need to add again
        }

        const li = document.createElement('li');
        li.className = 'nav-item';
        li.innerHTML = `
            <a class="nav-link d-flex align-items-center" href="#" data-friend-id="${friend.friend_id}">
                <img src="/static/profile_pictures/${friend.friend_profile_picture}" alt="${friend.friend_username}" class="rounded-circle me-2" width="32" height="32">
                <span class="flex-grow-1">${friend.friend_username}</span>
            </a>
        `;
        li.querySelector('a').addEventListener('click', (e) => {
            e.preventDefault();
            openChat(friend.friend_id, friend.friend_username);
        });
        chatList.appendChild(li);
    }

    function openChat(friendId, friendName) {
        currentChatId = friendId;
        startChat(friendId, friendName);
        const chatArea = document.getElementById('chatArea');
        if (chatArea) {
            chatArea.classList.remove('d-none');
        }
    }
});
