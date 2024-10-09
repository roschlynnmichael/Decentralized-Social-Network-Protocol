document.getElementById('resetPasswordForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const new_password = document.getElementById('new_password').value;
    const confirm_password = document.getElementById('confirm_password').value;
    const token = document.getElementById('token').value;

    if (new_password !== confirm_password) {
        document.getElementById('message').innerHTML = '<div class="alert alert-danger">Passwords do not match.</div>';
        return;
    }

    fetch(`/reset_password/${token}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            new_password: new_password
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            document.getElementById('message').innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
        } else {
            document.getElementById('message').innerHTML = `<div class="alert alert-success">${data.message} <a href="/login">Click here to login</a></div>`;
        }
    })
    .catch((error) => {
        console.error('Error:', error);
        document.getElementById('message').innerHTML = '<div class="alert alert-danger">An error occurred. Please try again.</div>';
    });
});