let chart;
let histChart;
let logs = [];
let filters = { filename: '', date: '' };

async function fetchStats() {
    const res = await fetch('/stats');
    const data = await res.json();
    if (data.error) {
        showError(data.error);
        return null;
    }
    return data;
}

async function fetchHistogram() {
    const res = await fetch('/histogram');
    const data = await res.json();
    return data;
}

async function fetchLogs() {
    let url = '/logs';
    const params = [];
    if (filters.filename) params.push('filename=' + encodeURIComponent(filters.filename));
    if (filters.date) params.push('date=' + encodeURIComponent(filters.date));
    if (params.length) url += '?' + params.join('&');
    const res = await fetch(url);
    const data = await res.json();
    logs = data;
    renderLogsTable();
}

async function fetchSummary() {
    const res = await fetch('/summary');
    const data = await res.json();
    if (!data.error) {
        document.getElementById('totalFiles').textContent = `Всего файлов: ${data.total_files}`;
        document.getElementById('totalDuration').textContent = `Общее время: ${formatDuration(data.total_duration)}`;
    }
}

function formatDuration(seconds) {
    if (seconds < 60) return `${seconds} сек`;
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    if (m < 60) return `${m} мин ${s} сек`;
    const h = Math.floor(m / 60);
    const mm = m % 60;
    return `${h} ч ${mm} мин ${s} сек`;
}

function showError(msg) {
    let errDiv = document.getElementById('errorDiv');
    if (!errDiv) {
        errDiv = document.createElement('div');
        errDiv.id = 'errorDiv';
        errDiv.style.color = 'red';
        errDiv.style.fontWeight = 'bold';
        document.body.insertBefore(errDiv, document.body.firstChild);
    }
    errDiv.textContent = msg;
    if (chart) chart.destroy();
    if (histChart) histChart.destroy();
}

function updateChart(data) {
    if (!data) return;
    const labels = Object.keys(data).sort();
    const values = labels.map(k => data[k]);
    const ctx = document.getElementById('logChart').getContext('2d');
    if (chart) chart.destroy();
    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Количество файлов (по минутам)',
                data: values,
                borderColor: '#36a2eb',
                backgroundColor: 'rgba(54,162,235,0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: true, position: 'top' }
            },
            scales: {
                x: { title: { display: true, text: 'Время (минуты)' } },
                y: { title: { display: true, text: 'Файлов' }, beginAtZero: true }
            }
        }
    });
}

function updateHistChart(data) {
    if (!data) return;
    const labels = Object.keys(data).sort();
    const values = labels.map(k => data[k]);
    const ctx = document.getElementById('histChart').getContext('2d');
    if (histChart) histChart.destroy();
    histChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Файлов за день',
                data: values,
                backgroundColor: 'rgba(255,184,108,0.7)',
                borderColor: '#ffb86c',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: true, position: 'top' }
            },
            scales: {
                x: { title: { display: true, text: 'Дата' } },
                y: { title: { display: true, text: 'Файлов' }, beginAtZero: true }
            }
        }
    });
}

function renderLogsTable() {
    const tbody = document.querySelector('#logsTable tbody');
    tbody.innerHTML = '';
    if (!logs.length) {
        tbody.innerHTML = '<tr><td colspan="5">Нет данных</td></tr>';
        return;
    }
    for (const log of logs) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${log.received_at}</td>
            <td>${log.filename}</td>
            <td>${log.duration}</td>
            <td>${log.size}</td>
            <td><button onclick="openLog('${log.filename}','${log.received_at}')">Открыть</button></td>
        `;
        tbody.appendChild(tr);
    }
}

async function openLog(filename, received_at) {
    const res = await fetch(`/log_text?filename=${encodeURIComponent(filename)}&received_at=${encodeURIComponent(received_at)}`);
    const data = await res.json();
    document.getElementById('logText').textContent = data.text || data.error || 'Нет данных';
    document.getElementById('logModal').style.display = 'flex';
}
function closeModal() {
    document.getElementById('logModal').style.display = 'none';
}

function applyFilters() {
    filters.filename = document.getElementById('filenameFilter').value.trim();
    filters.date = document.getElementById('dateFilter').value;
    fetchLogs();
}
function resetFilters() {
    document.getElementById('filenameFilter').value = '';
    document.getElementById('dateFilter').value = '';
    filters = { filename: '', date: '' };
    fetchLogs();
}

async function refresh() {
    const stats = await fetchStats();
    updateChart(stats);
    const hist = await fetchHistogram();
    updateHistChart(hist);
    await fetchLogs();
    await fetchSummary();
}

setInterval(refresh, 2000);
window.onload = refresh;
