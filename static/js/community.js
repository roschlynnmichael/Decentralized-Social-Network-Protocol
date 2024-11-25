document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    let communities = [];
    let currentCommunityId = null;
    
    // Listen for community stats updates
    socket.on('community_stats_update', (data) => {
        updateCommunityStats(data);
    });

    function updateCommunityStats(data) {
        // Update the sidebar item
        const sidebarItem = document.querySelector(`.community-item[data-community-id="${data.community_id}"]`);
        if (sidebarItem) {
            const statsElement = sidebarItem.querySelector('.text-sm.text-gray-500');
            if (statsElement) {
                statsElement.textContent = `${data.member_count} ${data.member_count === 1 ? 'member' : 'members'} • ${data.online_count} online`;
            }
        }

        // Update the header if this is the current community
        if (currentCommunityId === data.community_id) {
            const headerStatsElement = document.querySelector('#currentCommunityStats');
            if (headerStatsElement) {
                headerStatsElement.textContent = `${data.online_count} online • ${data.member_count} members`;
            }
        }
    }

    function displayMessage(data) {
        if (!messageArea) {
            console.error('Message area not found');
            return;
        }
        
        const messageElement = document.createElement('div');
        messageElement.className = 'message p-3 bg-white rounded-lg shadow-sm mb-3';
        
        const content = data.content || data.message || '';
        const username = data.username || 'Unknown User';
        const timestamp = data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
        
        messageElement.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0">
                    <div class="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-white text-sm">
                        ${username[0].toUpperCase()}
                    </div>
                </div>
                <div class="ml-3">
                    <p class="font-medium text-sm">${username}</p>
                    <p class="text-gray-600">${content}</p>
                    <p class="text-xs text-gray-400 mt-1">${timestamp}</p>
                </div>
            </div>
        `;
        
        messageArea.appendChild(messageElement);
        messageArea.scrollTop = messageArea.scrollHeight;
    }

    // Initialize chat handlers
    const messageForm = document.getElementById('messageForm');
    const messageInput = document.getElementById('messageInput');
    const messageArea = document.getElementById('messageArea');

    // Function to load communities
    async function loadCommunities() {
        try {
            const response = await fetch('/api/communities');
            if (!response.ok) {
                throw new Error('Failed to fetch communities');
            }
            
            communities = await response.json();
            const communitiesList = document.querySelector('.communities-list');
            
            if (!communitiesList) {
                console.error('Communities list element not found');
                return;
            }
            
            communitiesList.innerHTML = '';
            
            communities.forEach(community => {
                const communityElement = document.createElement('div');
                communityElement.className = 'community-item p-3 hover:bg-gray-50 cursor-pointer rounded-lg transition-colors';
                communityElement.dataset.communityId = community.id;
                
                communityElement.innerHTML = `
                    <div class="flex items-center space-x-3">
                        <div class="w-10 h-10 bg-primary rounded-lg flex items-center justify-center text-white">
                            <i class="fas fa-users"></i>
                        </div>
                        <div>
                            <h3 class="font-medium">${community.name}</h3>
                            <p class="text-sm text-gray-500">
                                ${community.member_count} ${community.member_count === 1 ? 'member' : 'members'} • ${community.online_count} online
                            </p>
                        </div>
                    </div>
                `;
                
                communityElement.addEventListener('click', () => {
                    joinCommunity(community.id);
                });
                
                communitiesList.appendChild(communityElement);
            });
        } catch (error) {
            console.error('Error loading communities:', error);
        }
    }

    // Update the socket event handlers
    socket.on('connect', () => {
        console.log('Socket connected');
    });

    // Add message handler
    socket.on('message', (data) => {
        console.log('Received message:', data);
        displayMessage(data);
    });

    // Handle message form submission
    if (messageForm) {
        messageForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const message = messageInput.value.trim();
            
            if (message && currentCommunityId) {
                console.log('Sending message:', message);
                socket.emit('message', {
                    room: `community_${currentCommunityId}`,
                    message: message,
                    content: message
                });
                
                messageInput.value = '';
            }
        });
    }

    // Join community function
    function joinCommunity(communityId) {
        console.log('Joining community:', communityId);
        if (currentCommunityId !== communityId) {
            if (currentCommunityId) {
                socket.emit('leave', { room: `community_${currentCommunityId}` });
            }
            currentCommunityId = communityId;
            
            // Clear message area
            if (messageArea) {
                messageArea.innerHTML = '';
            }
    
            // Join the Socket.IO room and request message history
            socket.emit('join_community', { 
                community_id: communityId 
            });
    
            socket.emit('get_message_history', { 
                community_id: communityId 
            });
    
            // Update UI
            document.querySelectorAll('.community-item').forEach(item => {
                const isSelected = item.dataset.communityId === communityId.toString();
                item.classList.toggle('bg-gray-50', isSelected);
                
                if (isSelected) {
                    const communityName = item.querySelector('h3').textContent;
                    const currentCommunityNameEl = document.getElementById('currentCommunityName');
                    if (currentCommunityNameEl) {
                        currentCommunityNameEl.textContent = communityName;
                    }

                    // Find the community data
                    const community = communities.find(c => c.id === communityId);
                    if (community) {
                        const headerStatsElement = document.querySelector('#currentCommunityStats');
                        if (headerStatsElement) {
                            headerStatsElement.textContent = `${community.online_count} online • ${community.member_count} members`;
                        }
                    }
                }
            });
        }
    }

    // Message history handler remains the same but now displayMessage is defined
    socket.on('message_history', (data) => {
        console.log('Received message history:', data);
        if (data.community_id === currentCommunityId && messageArea) {
            // Clear existing messages
            messageArea.innerHTML = '';
            
            // Display each message in history
            data.messages.forEach(message => {
                displayMessage(message);
            });
            
            // Scroll to bottom
            messageArea.scrollTop = messageArea.scrollHeight;
        }
    });

    // Load communities when page loads
    loadCommunities();
});