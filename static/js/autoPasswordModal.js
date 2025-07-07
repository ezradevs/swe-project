// Handles auto-opening of the change password modal based on URL flags (for error feedback)

// Auto-open change password modal if error flag is set
document.addEventListener('DOMContentLoaded', function () {
    // If the URL contains show_change_password_modal=1, open the change password modal
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('show_change_password_modal') === '1') {
        const modal = document.getElementById('changePasswordModal');
        if (modal) modal.style.display = 'block';
    }
});