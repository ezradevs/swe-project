// Provides live password validation feedback for the dashboard change password modal.
// Highlights password criteria as the user types.

const passwordInput = document.getElementById('new_password');
const criteria = {
    length: document.getElementById('length'),
    letter: document.getElementById('letter'),
    number: document.getElementById('number'),
    special: document.getElementById('special')
};

// Returns an object indicating which criteria are met
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
        // Update criteria color based on validity
        for (const key in criteria) {
            if (valid[key]) {
                criteria[key].style.color = 'green';
            } else {
                criteria[key].style.color = 'gray';
            }
        }
    });
}