document.getElementById('loginForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const identifier = document.getElementById('identifier').value;
    const password = document.getElementById('password').value;

    fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            identifier: identifier,
            password: password
        }),
    })
    .then(response => response.json().then(data => ({status: response.status, body: data})))
    .then(({status, body}) => {
        if (status === 200) {
            document.getElementById('message').innerHTML = `<div class="alert alert-success">${body.message}</div>`;
            if (body.redirect) {
                window.location.href = body.redirect;
            }
        } else {
            throw new Error(body.error || 'An unexpected error occurred');
        }
    })
    .catch((error) => {
        console.error('Error:', error);
        document.getElementById('message').innerHTML = `<div class="alert alert-danger">${error.message}</div>`;
    });
});