// This script scrolls to the fixtures table on the page when it is loaded.

// If the fixtures table is present, scroll to it on page load.
document.addEventListener('DOMContentLoaded', function () {
    var anchor = document.getElementById('fixtures-anchor');
    if (anchor) {
        // Use smooth scroll for better UX
        anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
});