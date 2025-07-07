// This script handles the modal logic for managing administrators in the admin portal.
// It manages opening/closing the edit admin modal, the change password modal, and the secure code modal for deleting admins.

document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.btn-edit-admin').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const adminId = btn.getAttribute('data-admin-id');
            const username = btn.getAttribute('data-admin-username');
            document.getElementById('editAdminId').value = adminId;
            document.getElementById('editAdminUsername').value = username;
            // Set the form action to the correct admin id
            document.getElementById('editAdminForm').action = '/edit_admin/' + adminId;
            document.getElementById('editAdminModal').style.display = 'block';
        });
    });
    document.getElementById('closeEditAdminModal').onclick = function () {
        document.getElementById('editAdminModal').style.display = 'none';
    };
    window.onclick = function (event) {
        if (event.target === document.getElementById('editAdminModal')) {
            document.getElementById('editAdminModal').style.display = 'none';
        }
    };
    // Change password modal logic
    document.querySelectorAll('.btn-change-admin-password').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const adminId = btn.getAttribute('data-admin-id');
            document.getElementById('changePasswordAdminId').value = adminId;
            document.getElementById('changeAdminPasswordModal').style.display = 'block';
        });
    });
    document.getElementById('closeChangeAdminPasswordModal').onclick = function () {
        document.getElementById('changeAdminPasswordModal').style.display = 'none';
    };
    window.addEventListener('click', function (event) {
        if (event.target === document.getElementById('changeAdminPasswordModal')) {
            document.getElementById('changeAdminPasswordModal').style.display = 'none';
        }
    });
    // Secure code modal logic for deleting admins
    const secureCodeModal = document.getElementById('secureCodeModal');
    const closeSecureCodeModal = document.getElementById('closeSecureCodeModal');
    const secureCodeForm = document.getElementById('secureCodeForm');
    let pendingDeleteForm = null;
    document.querySelectorAll('.btn-delete').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            const form = btn.closest('form');
            const row = btn.closest('tr');
            const username = row ? row.querySelector('td').innerText : '';
            const isSelf = username === window.sessionUsername;
            if (isSelf) {
                if (confirm('Delete your own administrator account? You will be logged out.')) {
                    form.submit();
                }
            } else {
                document.getElementById('secureDeleteAdminId').value = btn.getAttribute('data-admin-id') || form.action.split('/').pop();
                secureCodeModal.style.display = 'block';
                pendingDeleteForm = form;
            }
        });
    });
    if (closeSecureCodeModal) {
        closeSecureCodeModal.onclick = function () {
            secureCodeModal.style.display = 'none';
        };
    }
    window.addEventListener('click', function (event) {
        if (event.target === secureCodeModal) {
            secureCodeModal.style.display = 'none';
        }
    });
    if (secureCodeForm) {
        secureCodeForm.onsubmit = function (e) {
            e.preventDefault();
            // Add the secure code to the pending delete form and submit
            if (pendingDeleteForm) {
                let input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'secure_code';
                input.value = document.getElementById('secureCodeInput').value;
                pendingDeleteForm.appendChild(input);
                pendingDeleteForm.submit();
                secureCodeModal.style.display = 'none';
            }
        };
    }
    // Add Admin Modal logic
    const addAdminBtn = document.getElementById('addAdminBtn');
    const addAdminModal = document.getElementById('addAdminModal');
    const closeAddAdminModal = document.getElementById('closeAddAdminModal');
    if (addAdminBtn && addAdminModal && closeAddAdminModal) {
        addAdminBtn.addEventListener('click', function () {
            addAdminModal.style.display = 'block';
        });
        closeAddAdminModal.addEventListener('click', function () {
            addAdminModal.style.display = 'none';
        });
        window.addEventListener('click', function (event) {
            if (event.target === addAdminModal) {
                addAdminModal.style.display = 'none';
            }
        });
    }
});