// Handles the open/close logic for the change password modal on the dashboard or admin screens.

document.addEventListener('DOMContentLoaded', function () {
    const openBtn = document.getElementById('changePasswordBtn'); // Button to open modal
    const modal = document.getElementById('changePasswordModal'); // The modal element
    const closeBtn = document.getElementById('closeChangePasswordModal'); // The close (X) button

    if (openBtn && modal && closeBtn) {
        // Open modal when button is clicked
        openBtn.addEventListener('click', function (e) {
            e.preventDefault();
            modal.style.display = 'block';
        });
        // Close modal when close button is clicked
        closeBtn.addEventListener('click', function () {
            modal.style.display = 'none';
        });
        // Close modal when clicking outside the modal content
        window.addEventListener('click', function (event) {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    }
});