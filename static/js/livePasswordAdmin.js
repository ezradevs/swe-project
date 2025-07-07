// Provides live password validation feedback for the admin password change modal.
// Highlights password criteria as the user types.

const adminPasswordInput = document.getElementById('newAdminPassword');
const adminCriteria = {
    length: document.getElementById('admin-length'),
    letter: document.getElementById('admin-letter'),
    number: document.getElementById('admin-number'),
    special: document.getElementById('admin-special')
};

// Returns an object indicating which criteria are met
function validateAdminPassword(pw) {
    return {
        length: pw.length >= 8,
        letter: /[A-Za-z]/.test(pw),
        number: /\d/.test(pw),
        special: /[^A-Za-z0-9]/.test(pw)
    };
}

if (adminPasswordInput) {
    adminPasswordInput.addEventListener('input', function () {
        const pw = adminPasswordInput.value;
        const valid = validateAdminPassword(pw);
        // Update criteria color based on validity
        for (const key in adminCriteria) {
            if (valid[key]) {
                adminCriteria[key].style.color = 'green';
            } else {
                adminCriteria[key].style.color = 'gray';
            }
        }
    });
}