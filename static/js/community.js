document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    
    // Initialize chat handlers
    const messageForm = document.getElementById('messageForm');
    const messageInput = document.getElementById('messageInput');
    const messageArea = document.getElementById('messageArea');
    let currentCommunityId = null;

    // Function to load communities
    async function loadCommunities() {
        try {
            const response = await fetch('/api/communities');
            if (!response.ok) {
                throw new Error('Failed to fetch communities');
            }
            
            const communities = await response.json();
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
                                ${community.member_count || 0} members • ${community.online_count || 0} online
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

    // Add message socket listener
    socket.on('message', (data) => {
        console.log('Received message:', data);
        if (!messageArea) {
            console.error('Message area not found in DOM');
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
            socket.emit('join', { room: `community_${communityId}` });
            
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
                }
            });
            
            // Clear message area
            if (messageArea) {
                messageArea.innerHTML = '';
            }
        }
    }

    // Load communities when page loads
    loadCommunities();
});