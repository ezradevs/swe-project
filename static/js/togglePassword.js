// Toggle password visibility in login and signup forms.
// It allows users to see or hide their passwords by clicking an eye icon next to the password input fields.

// Toggle password visibility for login
const loginPassword = document.getElementById('login-password');
const loginEye = document.getElementById('login-eye');
if (loginPassword && loginEye) {
    loginEye.addEventListener('click', function () {
        const isHidden = loginPassword.type === 'password';
        loginPassword.type = isHidden ? 'text' : 'password';
        loginEye.classList.toggle('fa-eye');
        loginEye.classList.toggle('fa-eye-slash');
    });
}

// Toggle password visibility for signup
const signupPassword = document.getElementById('signup-password');
const signupEye = document.getElementById('signup-eye');
if (signupPassword && signupEye) {
    signupEye.addEventListener('click', function () {
        const isHidden = signupPassword.type === 'password';
        signupPassword.type = isHidden ? 'text' : 'password';
        signupEye.classList.toggle('fa-eye');
        signupEye.classList.toggle('fa-eye-slash');
    });
}