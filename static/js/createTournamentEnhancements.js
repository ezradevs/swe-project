document.addEventListener('DOMContentLoaded', () => {
  const previewMap = {};
  document.querySelectorAll('[data-preview-target]').forEach((el) => {
    previewMap[el.dataset.previewTarget] = el;
  });

  const formatTiles = Array.from(document.querySelectorAll('.format-tile'));
  const locationRadios = Array.from(document.querySelectorAll('.location-radio'));
  const customLocationGroup = document.querySelector('.custom-location-group');
  const customLocationInput = document.getElementById('custom_location');
  const inputWatchers = Array.from(document.querySelectorAll('.input-watch'));

  const toNiceDate = (value) => {
    if (!value) return '';
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return value;
    return dt.toLocaleDateString(undefined, {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const updatePreview = (key, value) => {
    if (!previewMap[key]) return;
    if (key === 'date') {
      previewMap[key].textContent = value ? toNiceDate(value) : 'Pick a date';
      return;
    }
    const fallback = {
      name: 'Tournament name pending',
      location: 'Select or enter a venue',
      format: 'Choose a format'
    };
    const cleanValue = value && value.trim() ? value : fallback[key] || '';
    previewMap[key].textContent = cleanValue;
  };

  const setFieldCompletion = (input, value) => {
    if (!input.classList.contains('input-watch')) return;
    const hasValue = input.type === 'radio' ? input.checked : Boolean(value && value.trim());
    if (hasValue) {
      input.classList.add('is-complete');
    } else {
      input.classList.remove('is-complete');
    }
  };

  const syncFormatTiles = () => {
    formatTiles.forEach((tile) => {
      const radio = tile.querySelector('input[type="radio"]');
      tile.classList.toggle('is-selected', radio && radio.checked);
      if (radio && radio.checked) {
        updatePreview('format', radio.value);
      }
    });
  };

  const toggleCustomLocation = (show) => {
    if (!customLocationGroup) return;
    customLocationGroup.setAttribute('data-visible', show ? 'true' : 'false');
    if (!show) {
      if (customLocationInput) {
        customLocationInput.value = '';
        customLocationInput.classList.remove('is-complete');
      }
    }
  };

  locationRadios.forEach((radio) => {
    radio.addEventListener('change', () => {
      if (!radio.checked) return;
      if (radio.value === 'custom') {
        toggleCustomLocation(true);
        if (customLocationInput) {
          customLocationInput.focus();
          updatePreview('location', customLocationInput.value);
          setFieldCompletion(customLocationInput, customLocationInput.value);
        }
      } else {
        toggleCustomLocation(false);
        updatePreview('location', radio.value);
        setFieldCompletion(radio, radio.value);
      }
    });
  });

  if (customLocationInput) {
    customLocationInput.addEventListener('input', () => {
      const customRadio = locationRadios.find((radio) => radio.value === 'custom');
      if (customRadio && !customRadio.checked) {
        customRadio.checked = true;
        toggleCustomLocation(true);
      }
      updatePreview('location', customLocationInput.value);
      setFieldCompletion(customLocationInput, customLocationInput.value);
    });
  }

  inputWatchers.forEach((input) => {
    const handler = () => {
      if (input.type === 'radio' && !input.checked) return;
      const key = input.dataset.preview;
      if (key) {
        updatePreview(key, input.value);
      }
      setFieldCompletion(input, input.value);
      if (input.classList.contains('format-radio')) {
        syncFormatTiles();
      }
    };
    const eventName = input.type === 'radio' ? 'change' : 'input';
    input.addEventListener(eventName, handler);
    // Initial state
    handler();
  });

  // Initialise location preview based on pre-selected radio
  const selectedRadio = locationRadios.find((radio) => radio.checked);
  if (selectedRadio && selectedRadio.value !== 'custom') {
    updatePreview('location', selectedRadio.value);
  }
  if (selectedRadio && selectedRadio.value === 'custom' && customLocationInput) {
    toggleCustomLocation(true);
    updatePreview('location', customLocationInput.value);
  }

  syncFormatTiles();
  updatePreview('date', document.getElementById('date')?.value || '');
  updatePreview('name', document.getElementById('name')?.value || '');
});
