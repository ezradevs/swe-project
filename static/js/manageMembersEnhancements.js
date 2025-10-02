const MembersEnhancements = (() => {
  const table = document.getElementById('membersTable');
  if (!table) return; // nothing to do

  const rows = Array.from(table.querySelectorAll('tbody tr'));
  const searchInput = document.getElementById('memberSearch');
  const ratingMinInput = document.getElementById('ratingMin');
  const ratingMaxInput = document.getElementById('ratingMax');
  const resetBtn = document.getElementById('resetFiltersBtn');
  const emptyState = document.getElementById('membersEmptyState');
  const headers = Array.from(table.querySelectorAll('thead th[data-sort-key]'));

  let currentSort = { key: 'rating', direction: 'desc' };

  const normalise = (value) => value.toLowerCase().trim();

  const applyFilters = () => {
    const query = normalise(searchInput?.value || '');
    const minRating = parseInt(ratingMinInput?.value || '', 10);
    const maxRating = parseInt(ratingMaxInput?.value || '', 10);
    let visibleCount = 0;

    rows.forEach((row) => {
      const name = normalise(row.dataset.memberName || '');
      const email = normalise(row.dataset.memberEmail || '');
      const rating = parseInt(row.dataset.memberRating || '0', 10);
      const matchQuery = !query || name.includes(query) || email.includes(query);
      const matchMin = Number.isNaN(minRating) || rating >= minRating;
      const matchMax = Number.isNaN(maxRating) || rating <= maxRating;
      const shouldShow = matchQuery && matchMin && matchMax;
      row.style.display = shouldShow ? '' : 'none';
      if (shouldShow) visibleCount += 1;
    });

    if (emptyState) {
      emptyState.style.display = visibleCount === 0 ? 'flex' : 'none';
    }
  };

  const resetFilters = () => {
    if (searchInput) searchInput.value = '';
    if (ratingMinInput) ratingMinInput.value = '';
    if (ratingMaxInput) ratingMaxInput.value = '';
    applyFilters();
  };

  const sortRows = (key, direction) => {
    const multiplier = direction === 'asc' ? 1 : -1;
    const getValue = (row) => {
      switch (key) {
        case 'name':
          return (row.dataset.memberName || '').toLowerCase();
        case 'email':
          return (row.dataset.memberEmail || '').toLowerCase();
        case 'rating':
          return parseInt(row.dataset.memberRating || '0', 10);
        case 'joined':
          return new Date(row.dataset.memberJoined || '').getTime();
        default:
          return row.dataset.memberId || '';
      }
    };

    const sorted = [...rows].sort((a, b) => {
      const aVal = getValue(a);
      const bVal = getValue(b);
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return (aVal - bVal) * multiplier;
      }
      if (aVal > bVal) return 1 * multiplier;
      if (aVal < bVal) return -1 * multiplier;
      return 0;
    });

    const tbody = table.querySelector('tbody');
    sorted.forEach((row) => tbody.appendChild(row));
  };

  const updateSortIndicators = (activeKey, direction) => {
    headers.forEach((header) => {
      header.classList.remove('sort-asc', 'sort-desc');
      if (header.dataset.sortKey === activeKey) {
        header.classList.add(direction === 'asc' ? 'sort-asc' : 'sort-desc');
      }
    });
  };

  const handleSort = (event) => {
    const header = event.currentTarget;
    const key = header.dataset.sortKey;
    if (!key) return;
    let direction = 'asc';
    if (currentSort.key === key && currentSort.direction === 'asc') {
      direction = 'desc';
    }
    currentSort = { key, direction };
    sortRows(key, direction);
    updateSortIndicators(key, direction);
    applyFilters();
  };

  // Attach listeners
  if (searchInput) searchInput.addEventListener('input', applyFilters);
  if (ratingMinInput) ratingMinInput.addEventListener('input', applyFilters);
  if (ratingMaxInput) ratingMaxInput.addEventListener('input', applyFilters);
  if (resetBtn) resetBtn.addEventListener('click', resetFilters);
  headers.forEach((header) => header.addEventListener('click', handleSort));

  // Initial state
  sortRows(currentSort.key, currentSort.direction);
  updateSortIndicators(currentSort.key, currentSort.direction);
  applyFilters();
})();
