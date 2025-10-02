const initMemberModals = () => {
  const addModal = document.getElementById('addMemberModal');
  const addButton = document.getElementById('addMemberBtn');
  const addClose = document.getElementById('closeModal');

  const editModal = document.getElementById('editMemberModal');
  const editForm = document.getElementById('editMemberForm');
  const editClose = document.getElementById('closeEditModal');
  const editName = document.getElementById('edit-name');
  const editEmail = document.getElementById('edit-email');
  const editRating = document.getElementById('edit-rating');

  const showModal = (modal) => {
    if (!modal) return;
    modal.classList.remove('modal-hide');
    modal.style.display = 'block';
  };

  const hideModal = (modal) => {
    if (!modal) return;
    modal.style.display = 'none';
    modal.classList.add('modal-hide');
  };

  if (addModal && addButton && addClose) {
    addButton.addEventListener('click', () => showModal(addModal));
    addClose.addEventListener('click', () => hideModal(addModal));
    window.addEventListener('click', (event) => {
      if (event.target === addModal) hideModal(addModal);
    });
  }

  const handleEditClick = (event) => {
    const button = event.currentTarget;
    const row = button.closest('tr');
    if (!row || !editModal || !editForm || !editName || !editEmail || !editRating) return;

    const memberId = row.dataset.memberId;
    editName.value = row.dataset.memberName || '';
    editEmail.value = row.dataset.memberEmail || '';
    editRating.value = row.dataset.memberRating || '';
    editForm.action = `/edit_member/${memberId}`;
    showModal(editModal);
  };

  if (editModal && editForm && editClose) {
    editClose.addEventListener('click', () => hideModal(editModal));
    window.addEventListener('click', (event) => {
      if (event.target === editModal) hideModal(editModal);
    });

    document.querySelectorAll('.btn-edit').forEach((button) => {
      button.addEventListener('click', handleEditClick);
    });
  }
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initMemberModals);
} else {
  initMemberModals();
}
