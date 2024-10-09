document.getElementById('resetPasswordRequestForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;

    fetch('/reset_password_request', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            email: email
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            document.getElementById('message').innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
        } else {
            document.getElementById('message').innerHTML = `<div class="alert alert-success">${data.message}</div>`;
        }
    })
    .catch((error) => {
        console.error('Error:', error);
        document.getElementById('message').innerHTML = '<div class="alert alert-danger">An error occurred. Please try again.</div>';
    });
});