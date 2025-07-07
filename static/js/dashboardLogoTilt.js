// Adds a 3D tilt effect to the dashboard logo based on mouse position for a modern UI feel.

document.addEventListener('DOMContentLoaded', function () {
    const logo = document.querySelector('.dashboard-logo');
    if (!logo) return;

    // Enable 3D transform
    logo.style.transformStyle = 'preserve-3d';

    // On mouse move, calculate rotation based on cursor position
    logo.addEventListener('mousemove', function (e) {
        const rect = logo.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        // Exaggerate the effect: increase max degrees
        const rotateY = ((x - centerX) / centerX) * 22; // max 22deg
        const rotateX = -((y - centerY) / centerY) * 22; // max 22deg

        logo.style.transform = `perspective(300px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.12)`;
        logo.style.boxShadow = '0 12px 40px rgba(37,99,235,0.22), 0 2px 12px rgba(0,0,0,0.13)';
    });

    // Reset transform and shadow on mouse leave
    logo.addEventListener('mouseleave', function () {
        logo.style.transform = '';
        logo.style.boxShadow = '';
    });
});