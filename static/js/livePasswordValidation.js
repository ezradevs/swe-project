// This script validates a password input in real-time and enables/disables the submit button based on criteria.

const passwordInput = document.getElementById('signup-password');
const submitBtn = document.getElementById('submitBtn');
const criteria = {
    length: document.getElementById('length'),
    letter: document.getElementById('letter'),
    number: document.getElementById('number'),
    special: document.getElementById('special')
};

function validatePassword(pw) {
    return {
        length: pw.length >= 8,
        letter: /[A-Za-z]/.test(pw),
        number: /\d/.test(pw),
        special: /[^A-Za-z0-9]/.test(pw)
    };
}

if (passwordInput) {
    passwordInput.addEventListener('input', function () {
        const pw = passwordInput.value;
        const valid = validatePassword(pw);
        let allValid = true;
        for (const key in criteria) {
            if (valid[key]) {
                criteria[key].style.color = 'green';
            } else {
                criteria[key].style.color = 'gray';
                allValid = false;
            }
        }
        submitBtn.disabled = !allValid;
    });
}