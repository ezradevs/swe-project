const initAdminTableEnhancements = () => {
  const table = document.getElementById('adminsTable');
  const searchInput = document.getElementById('adminSearch');
  if (!table) return;

  const rows = Array.from(table.querySelectorAll('tbody tr'));
  const usernameHeader = table.querySelector('th[data-sort-key="username"]');

  const filterRows = () => {
    const query = (searchInput?.value || '').trim().toLowerCase();
    rows.forEach((row) => {
      const username = (row.dataset.adminUsername || '').toLowerCase();
      row.style.display = !query || username.includes(query) ? '' : 'none';
    });
  };

  const sortRows = (direction = 'asc') => {
    const multiplier = direction === 'asc' ? 1 : -1;
    const sorted = [...rows].sort((a, b) => {
      const aName = (a.dataset.adminUsername || '').toLowerCase();
      const bName = (b.dataset.adminUsername || '').toLowerCase();
      if (aName > bName) return 1 * multiplier;
      if (aName < bName) return -1 * multiplier;
      return 0;
    });
    const tbody = table.querySelector('tbody');
    sorted.forEach((row) => tbody.appendChild(row));
  };

  let currentDirection = 'asc';

  if (usernameHeader) {
    usernameHeader.addEventListener('click', () => {
      currentDirection = currentDirection === 'asc' ? 'desc' : 'asc';
      sortRows(currentDirection);
      usernameHeader.classList.toggle('sort-asc', currentDirection === 'asc');
      usernameHeader.classList.toggle('sort-desc', currentDirection === 'desc');
    });
    // initial sort indicator
    usernameHeader.classList.add('sort-asc');
  }

  if (searchInput) {
    searchInput.addEventListener('input', filterRows);
  }

  // initial setup
  sortRows(currentDirection);
  filterRows();
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAdminTableEnhancements);
} else {
  initAdminTableEnhancements();
}
