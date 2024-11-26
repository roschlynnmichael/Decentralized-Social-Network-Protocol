document.addEventListener('DOMContentLoaded', function() {
    const userSelect = document.getElementById('userSelect');
    const filesList = document.getElementById('filesList');
    const selectedBucketHash = document.getElementById('selectedBucketHash');
    let peerFiles = {};

    // Load peer files
    function loadPeerFiles() {
        fetch('/api/peer_files')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    peerFiles = data.users;
                    updateUserSelect();
                } else {
                    console.error('Error loading peer files:', data.error);
                }
            })
            .catch(error => console.error('Error:', error));
    }

    // Update user select dropdown
    function updateUserSelect() {
        userSelect.innerHTML = '<option value="">Select a peer...</option>';
        Object.entries(peerFiles).forEach(([userId, userData]) => {
            const option = document.createElement('option');
            option.value = userId;
            option.textContent = `${userData.username}`;
            userSelect.appendChild(option);
        });
    }

    // Display files for selected user
    function displayFiles(userId) {
        filesList.innerHTML = '';
        selectedBucketHash.textContent = '';

        if (!userId) {
            filesList.innerHTML = '<p class="text-gray-500 text-center">Select a peer to view their files</p>';
            return;
        }

        const userData = peerFiles[userId];
        if (!userData) {
            console.error('No user data found for:', userId);
            return;
        }

        // Display full bucket hash
        selectedBucketHash.textContent = `Bucket Hash: ${userData.bucket_hash}`;
        console.log('Files for user:', userData.username, userData.files);

        if (!userData.files || userData.files.length === 0) {
            filesList.innerHTML = '<p class="text-gray-500 text-center">No files available</p>';
            return;
        }

        // Helper function to format file size
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        userData.files.forEach(file => {
            const fileElement = document.createElement('div');
            fileElement.className = 'flex justify-between items-center p-2 border rounded-lg mb-2 bg-white hover:bg-gray-50';
            fileElement.innerHTML = `
                <div class="flex-1">
                    <p class="font-medium text-gray-800">${file.name}</p>
                    <div class="flex items-center text-sm text-gray-500 space-x-4">
                        <span>Size: ${formatFileSize(file.size)}</span>
                        <span>Added: ${new Date(file.timestamp * 1000).toLocaleString()}</span>
                    </div>
                </div>
                <a href="/api/peer_file/${userId}/${file.id}/${encodeURIComponent(file.name)}" 
                   class="text-blue-600 hover:text-blue-800 p-2"
                   download>
                    <i class="fas fa-download text-lg"></i>
                </a>
            `;
            filesList.appendChild(fileElement);
        });
    }

    // Event Listeners
    userSelect.addEventListener('change', (e) => {
        const userId = e.target.value;
        displayFiles(userId);
    });

    // Initial load
    loadPeerFiles();

    // Refresh every 30 seconds
    setInterval(loadPeerFiles, 30000);
});