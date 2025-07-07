// Handles auto-opening of admin password and add admin modals based on URL flags (for error feedback)

// Auto-open change admin password modal if error flag is set and set admin_id
document.addEventListener('DOMContentLoaded', function () {
    // If the URL contains show_change_admin_password_modal, open the change admin password modal and set admin_id
    const urlParams = new URLSearchParams(window.location.search);
    const adminId = urlParams.get('show_change_admin_password_modal');
    if (adminId) {
        const modal = document.getElementById('changeAdminPasswordModal');
        const adminIdInput = document.getElementById('changePasswordAdminId');
        if (modal) modal.style.display = 'block';
        if (adminIdInput) adminIdInput.value = adminId;
    }
});

// Auto-open Add Admin modal if error flag is set
document.addEventListener('DOMContentLoaded', function () {
    // If the URL contains show_add_admin_modal, open the Add Admin modal (for error feedback)
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('show_add_admin_modal')) {
        const addAdminModal = document.getElementById('addAdminModal');
        if (addAdminModal) addAdminModal.style.display = 'block';
    }
});