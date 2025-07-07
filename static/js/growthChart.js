
// Realistic, non-linear Membership Growth Chart (ending at 118 members)
const growthData = {
    labels: [
        '2024-08', '2024-09', '2024-10', '2024-11', '2024-12', '2025-01',
        '2025-02', '2025-03', '2025-04', '2025-05', '2025-06', '2025-07'
    ],
    values: [8, 13, 19, 27, 36, 44, 56, 68, 80, 93, 105, 118]
};
const ctxGrowth = document.getElementById('growthChart').getContext('2d');
new Chart(ctxGrowth, {
    type: 'line',
    data: {
        labels: growthData.labels,
        datasets: [{
            label: 'Total Members',
            data: growthData.values,
            backgroundColor: 'rgba(37,99,235,0.12)',
            borderColor: '#2563eb',
            borderWidth: 2,
            pointRadius: 4,
            fill: true,
            tension: 0.3
        }]
    },
    options: {
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { stepSize: 20 } } }
    }
});