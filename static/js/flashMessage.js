// Handles the fade-in and fade-out animation for flash messages (alerts) in the UI.

document.addEventListener('DOMContentLoaded', () => {
  const flashMessages = document.querySelectorAll('.flash-message');
  flashMessages.forEach((el) => {
    // Trigger fade-in
    requestAnimationFrame(() => {
      el.style.opacity = '0.97';
    });

    // Trigger fade-out after 4 seconds
    setTimeout(() => {
      el.style.opacity = '0';
      // Remove the element after the fade-out transition ends
      el.addEventListener('transitionend', () => {
        el.remove();
      });
    }, 4000); // 4000ms = 4 seconds
  });
});