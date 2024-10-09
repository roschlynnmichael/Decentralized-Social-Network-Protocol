document.getElementById('registerForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    fetch('/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: username,
            email: email,
            password: password
        }),
    })
    .then(response => {
        console.log('Response status:', response.status);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Response data:', data);
        if (data.error) {
            document.getElementById('message').innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
        } else if (data.message) {
            document.getElementById('message').innerHTML = `<div class="alert alert-success">${data.message}</div>`;
            document.getElementById('registerForm').reset();
        } else {
            console.error('Unexpected response structure:', data);
            throw new Error('Unexpected response structure from server');
        }
    })
    .catch((error) => {
        console.error('Error:', error);
        document.getElementById('message').innerHTML = '<div class="alert alert-danger">An error occurred. Please try again.</div>';
    });
});