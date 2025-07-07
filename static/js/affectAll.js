// This script provides utility functions for selecting or clearing all participant checkboxes
// in the manage players screen of the admin portal.

// Wait for the DOM to be fully loaded before running the script
document.addEventListener('DOMContentLoaded', function () {
    // Get the 'Select All' and 'Clear All' buttons
    const selectAllBtn = document.querySelector('.select-all-btn');
    const clearAllBtn = document.querySelector('.clear-all-btn');
    // Get all participant checkboxes in the table
    const checkboxes = document.querySelectorAll('input[type="checkbox"][name="participants"]');

    // If the 'Select All' button exists, set its click handler to check all checkboxes
    if (selectAllBtn) {
        selectAllBtn.onclick = function () {
            checkboxes.forEach(cb => cb.checked = true);
        };
    }
    // If the 'Clear All' button exists, set its click handler to uncheck all checkboxes
    if (clearAllBtn) {
        clearAllBtn.onclick = function () {
            checkboxes.forEach(cb => cb.checked = false);
        };
    }
});