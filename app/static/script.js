let chart;

async function fetchStats() {
    const res = await fetch('/stats');
    const data = await res.json();
    return data;
}

function updateChart(data) {
    const labels = Object.keys(data).sort();
    const values = labels.map(k => data[k]);
    if (!chart) {
        const ctx = document.getElementById('logChart').getContext('2d');
        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Количество файлов',
                    data: values,
                    borderColor: 'blue',
                    backgroundColor: 'rgba(0,0,255,0.1)',
                    fill: true
                }]
            },
            options: {
                responsive: false,
                scales: {
                    x: { title: { display: true, text: 'Время (минуты)' } },
                    y: { title: { display: true, text: 'Файлов' }, beginAtZero: true }
                }
            }
        });
    } else {
        chart.data.labels = labels;
        chart.data.datasets[0].data = values;
        chart.update();
    }
}

async function refresh() {
    const stats = await fetchStats();
    updateChart(stats);
}

setInterval(refresh, 1000);
window.onload = refresh;
