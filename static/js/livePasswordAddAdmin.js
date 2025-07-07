// Provides live password validation feedback for the Add Administrator modal.
// Highlights password criteria as the user types.

const addAdminPasswordInput = document.getElementById('addAdminPassword');
const addAdminCriteria = {
    length: document.getElementById('add-admin-length'),
    letter: document.getElementById('add-admin-letter'),
    number: document.getElementById('add-admin-number'),
    special: document.getElementById('add-admin-special')
};

// Returns an object indicating which criteria are met
function validateAddAdminPassword(pw) {
    return {
        length: pw.length >= 8,
        letter: /[A-Za-z]/.test(pw),
        number: /\d/.test(pw),
        special: /[^A-Za-z0-9]/.test(pw)
    };
}

if (addAdminPasswordInput) {
    addAdminPasswordInput.addEventListener('input', function () {
        const pw = addAdminPasswordInput.value;
        const valid = validateAddAdminPassword(pw);
        // Update criteria color based on validity
        for (const key in addAdminCriteria) {
            if (valid[key]) {
                addAdminCriteria[key].style.color = 'green';
            } else {
                addAdminCriteria[key].style.color = 'gray';
            }
        }
    });
}