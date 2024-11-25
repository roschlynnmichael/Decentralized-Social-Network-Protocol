// Global variables
let socket;
let communities = [];
let currentCommunityId = null;
let messageArea;
let messageForm;
let messageInput;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Socket.IO
    socket = io();
    
    // Get DOM elements
    messageArea = document.getElementById('messageArea');
    messageForm = document.getElementById('messageForm');
    messageInput = document.getElementById('messageInput');
    const createCommunityBtn = document.getElementById('createCommunityBtn');
    const createCommunityModal = document.getElementById('createCommunityModal');
    const createCommunityForm = document.getElementById('createCommunityForm');
    const addMembersBtn = document.getElementById('addMembersBtn');
    const addMembersModal = document.getElementById('addMembersModal');
    const addMembersForm = document.getElementById('addMembersForm');

    // Socket event listeners
    socket.on('connect', () => console.log('Socket connected'));
    socket.on('message', displayMessage);
    socket.on('message_history', handleMessageHistory);
    socket.on('community_stats_update', updateCommunityStats);

    // UI event listeners
    createCommunityBtn.addEventListener('click', () => {
        createCommunityModal.classList.remove('hidden');
        loadAvailableUsers();
    });

    createCommunityForm.addEventListener('submit', handleCreateCommunity);
    
    if (messageForm) {
        messageForm.addEventListener('submit', handleMessageSubmit);
    }

    addMembersBtn.addEventListener('click', () => {
        addMembersModal.classList.remove('hidden');
        loadAvailableUsersForAdd();
    });

    addMembersForm.addEventListener('submit', handleAddMembers);

    // Close modal when clicking outside
    createCommunityModal.addEventListener('click', (e) => {
        if (e.target === createCommunityModal) {
            createCommunityModal.classList.add('hidden');
        }
    });

    addMembersModal.addEventListener('click', (e) => {
        if (e.target === addMembersModal) {
            addMembersModal.classList.add('hidden');
        }
    });

    // Load initial communities
    loadCommunities();
});

// Community Management Functions
async function loadCommunities() {
    try {
        const response = await fetch('/api/communities');
        communities = await response.json();
        
        const communitiesList = document.querySelector('.communities-list');
        if (!communitiesList) return;
        
        communitiesList.innerHTML = '';
        
        communities.forEach(community => {
            const communityElement = document.createElement('div');
            communityElement.className = 'community-item p-3 hover:bg-gray-50 rounded-lg cursor-pointer';
            communityElement.dataset.communityId = community.id;
            
            communityElement.innerHTML = `
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 bg-primary rounded-lg flex items-center justify-center text-white">
                        <i class="fas fa-users"></i>
                    </div>
                    <div>
                        <h3 class="font-medium">${community.name}</h3>
                        <p class="text-sm text-gray-500">
                            ${community.member_count} ${community.member_count === 1 ? 'member' : 'members'} • 
                            ${community.online_count} online
                        </p>
                    </div>
                </div>
            `;
            
            communityElement.addEventListener('click', () => joinCommunity(community.id));
            communitiesList.appendChild(communityElement);
        });
        
        // Join first community by default
        if (communities.length > 0 && !currentCommunityId) {
            joinCommunity(communities[0].id);
        }
    } catch (error) {
        console.error('Error loading communities:', error);
    }
}

async function loadCommunityMembers(communityId) {
    try {
        const response = await fetch(`/api/communities/${communityId}/members`);
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to load members');
        }

        const data = await response.json();
        const members = Array.isArray(data) ? data : [];
        
        const currentUserId = parseInt(currentUser.id);
        const currentUserMember = members.find(m => parseInt(m.user_id) === currentUserId);
        const isAdmin = currentUserMember?.role === 'admin';
        
        // Update members sidebar
        const membersList = document.getElementById('membersList');
        membersList.innerHTML = '';
        
        members.forEach(member => {
            const memberElement = document.createElement('div');
            memberElement.className = 'flex items-center justify-between p-2 hover:bg-gray-50 rounded';
            
            memberElement.innerHTML = `
                <div class="flex items-center space-x-2">
                    <div class="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-white">
                        ${member.username ? member.username[0].toUpperCase() : '?'}
                    </div>
                    <div class="flex flex-col">
                        <span class="text-sm font-medium">${member.username || 'Unknown User'}</span>
                        <span class="text-xs text-gray-500">
                            ${member.role === 'admin' ? 
                                '<span class="text-blue-600">Admin</span>' : 
                                'Member'}
                        </span>
                    </div>
                </div>
                ${isAdmin && parseInt(member.user_id) !== currentUserId && member.role !== 'admin' ? `
                    <button 
                        class="text-red-500 hover:text-red-600" 
                        onclick="removeMember(${communityId}, ${member.user_id})"
                    >
                        <i class="fas fa-times"></i>
                    </button>
                ` : ''}
            `;
            
            membersList.appendChild(memberElement);
        });

        // Show/hide Add Members button based on admin status
        const addMembersBtn = document.getElementById('addMembersBtn');
        if (addMembersBtn) {
            addMembersBtn.classList.toggle('hidden', !isAdmin);
        }
        
    } catch (error) {
        console.error('Error loading members:', error);
        const errorElement = document.createElement('div');
        errorElement.className = 'p-2 text-sm text-red-600';
        errorElement.textContent = 'Failed to load members. Please try again later.';
        document.getElementById('membersList').appendChild(errorElement);
    }
}
// Message Handling Functions
function displayMessage(data) {
    if (!messageArea) return;
    
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

// Event Handlers
async function handleCreateCommunity(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {
        name: formData.get('name'),
        description: formData.get('description'),
        members: Array.from(document.getElementById('memberSelect').selectedOptions).map(option => parseInt(option.value))
    };

    try {
        const response = await fetch('/api/communities', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            createCommunityModal.classList.add('hidden');
            e.target.reset();
            loadCommunities();
        } else {
            const error = await response.json();
            alert(error.error || 'Failed to create community');
        }
    } catch (error) {
        console.error('Error creating community:', error);
        alert('Failed to create community');
    }
}

function handleMessageSubmit(e) {
    e.preventDefault();
    const message = messageInput.value.trim();
    
    if (message && currentCommunityId) {
        socket.emit('message', {
            room: `community_${currentCommunityId}`,
            message: message,
            content: message
        });
        
        messageInput.value = '';
    }
}

function handleMessageHistory(data) {
    if (data.community_id === currentCommunityId && messageArea) {
        messageArea.innerHTML = '';
        data.messages.forEach(displayMessage);
        messageArea.scrollTop = messageArea.scrollHeight;
    }
}

// Utility Functions
async function loadAvailableUsers() {
    try {
        const response = await fetch('/api/users/available');
        const users = await response.json();
        
        const memberSelect = document.getElementById('memberSelect');
        memberSelect.innerHTML = '';
        
        users.forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = user.username;
            memberSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading available users:', error);
    }
}

function updateCommunityStats(data) {
    const sidebarItem = document.querySelector(`.community-item[data-community-id="${data.community_id}"]`);
    if (sidebarItem) {
        const statsElement = sidebarItem.querySelector('.text-sm.text-gray-500');
        if (statsElement) {
            statsElement.textContent = `${data.member_count} ${data.member_count === 1 ? 'member' : 'members'} • ${data.online_count} online`;
        }
    }

    if (currentCommunityId === data.community_id) {
        const headerStatsElement = document.querySelector('#currentCommunityStats');
        if (headerStatsElement) {
            headerStatsElement.textContent = `${data.online_count} online • ${data.member_count} members`;
        }
    }
}

function joinCommunity(communityId) {
    currentCommunityId = communityId;
    
    if (messageArea) {
        messageArea.innerHTML = '';
    }

    socket.emit('join_community', { community_id: communityId });
    socket.emit('get_message_history', { community_id: communityId });

    document.querySelectorAll('.community-item').forEach(item => {
        const isSelected = item.dataset.communityId === communityId.toString();
        item.classList.toggle('bg-gray-50', isSelected);
    });

    const community = communities.find(c => c.id === communityId);
    if (community) {
        const nameElement = document.getElementById('currentCommunityName');
        const statsElement = document.querySelector('#currentCommunityStats');
        
        if (nameElement) {
            nameElement.textContent = community.name;
        }
        if (statsElement) {
            statsElement.textContent = `${community.online_count} online • ${community.member_count} members`;
        }
    }

    loadCommunityMembers(communityId);
}

// Global function for removing members
window.removeMember = async function(communityId, userId) {
    if (!confirm('Are you sure you want to remove this member?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/communities/${communityId}/members/${userId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            loadCommunityMembers(communityId);
            loadCommunities();
        } else {
            const error = await response.json();
            alert(error.error);
        }
    } catch (error) {
        console.error('Error removing member:', error);
        alert('Failed to remove member');
    }
};

async function loadAvailableUsersForAdd() {
    try {
        const response = await fetch('/api/users/available');
        const users = await response.json();
        
        const memberSelect = document.getElementById('newMemberSelect');
        memberSelect.innerHTML = '';
        
        // Filter out users who are already members
        const currentMembers = await fetch(`/api/communities/${currentCommunityId}/members`);
        const membersData = await currentMembers.json();
        const memberIds = membersData.map(m => m.user_id.toString());
        
        users.filter(user => !memberIds.includes(user.id.toString()))
            .forEach(user => {
                const option = document.createElement('option');
                option.value = user.id;
                option.textContent = user.username;
                memberSelect.appendChild(option);
            });
    } catch (error) {
        console.error('Error loading available users:', error);
    }
}

async function handleAddMembers(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const selectedUsers = Array.from(document.getElementById('newMemberSelect').selectedOptions)
        .map(option => parseInt(option.value));
    
    try {
        const promises = selectedUsers.map(userId => 
            fetch(`/api/communities/${currentCommunityId}/members`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId })
            })
        );
        
        await Promise.all(promises);
        
        // Close modal and refresh
        document.getElementById('addMembersModal').classList.add('hidden');
        e.target.reset();
        loadCommunityMembers(currentCommunityId);
        loadCommunities();
    } catch (error) {
        console.error('Error adding members:', error);
        alert('Failed to add members');
    }
}
