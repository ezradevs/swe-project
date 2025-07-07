// This script handles the modal logic for adding and editing members in the admin portal.
// It manages opening/closing the add member modal, the edit member modal, and populating the edit form.

// --- Add Member Modal Logic ---
const modal = document.getElementById('addMemberModal'); // The modal element for adding a member
const btn = document.getElementById('addMemberBtn');     // The button that opens the add member modal
const close = document.getElementById('closeModal');     // The close (X) button in the add member modal

// When the add member button is clicked, show the modal
btn.onclick = () => modal.style.display = 'block';
// When the close button is clicked, hide the modal
close.onclick = () => modal.style.display = 'none';
// When clicking outside the modal content, hide the modal
window.onclick = (e) => { if (e.target === modal) modal.style.display = 'none'; };

// --- Edit Member Modal Logic ---
const editModal = document.getElementById('editMemberModal'); // The modal element for editing a member
const closeEdit = document.getElementById('closeEditModal');  // The close (X) button in the edit member modal
// When the close button is clicked, hide the edit modal
closeEdit.onclick = () => editModal.style.display = 'none';
// When clicking outside the edit modal content, hide the edit modal
window.addEventListener('click', (e) => { if (e.target === editModal) editModal.style.display = 'none'; });

// Function to open the edit member modal and populate it with the selected member's data
function openEditModal(btn) {
    // Find the table row for the clicked edit button
    const row = btn.closest('tr');
    // Extract member data from data attributes on the row
    const id = row.getAttribute('data-member-id');
    const name = row.getAttribute('data-member-name');
    const email = row.getAttribute('data-member-email');
    const rating = row.getAttribute('data-member-rating');
    // Populate the edit form fields with the member's data
    document.getElementById('edit-name').value = name;
    document.getElementById('edit-email').value = email;
    document.getElementById('edit-rating').value = rating;
    // Set the form action to the correct member ID for submission
    const form = document.getElementById('editMemberForm');
    form.action = `/edit_member/${id}`;
    // Show the edit member modal
    editModal.style.display = 'block';
}