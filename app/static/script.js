let chart;
let histChart;
let logs = [];
let filters = { filename: '', date: '' };

const UI_CONST = {
    UPDATE_INTERVAL_MS: 60000, // 1 минута
    NO_DATA_TEXT: 'Нет данных',
    DELETE_CONFIRM_TEXT: 'Удалить лог?',
    DELETE_ERROR_TEXT: 'Ошибка удаления',
    TOTAL_FILES_LABEL: 'Всего файлов',
    TOTAL_DURATION_LABEL: 'Общее время',
    DURATION_SEC: 'сек',
    DURATION_MIN: 'мин',
    DURATION_HOUR: 'ч',
    OPEN_BTN_LABEL: 'Открыть',
    DELETE_BTN_LABEL: 'Удалить',
    CHART_LABEL_MINUTES: 'Количество файлов (по минутам)',
    CHART_LABEL_DAYS: 'Файлов за день',
    CHART_X_MINUTES: 'Время (минуты)',
    CHART_X_DAYS: 'Дата',
    CHART_Y_FILES: 'Файлов',
};

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
        document.getElementById('totalFiles').textContent = `${UI_CONST.TOTAL_FILES_LABEL}: ${data.total_files}`;
        document.getElementById('totalDuration').textContent = `${UI_CONST.TOTAL_DURATION_LABEL}: ${formatDuration(data.total_duration)}`;
    }
}

function formatDuration(seconds) {
    if (seconds < 60) return `${seconds} ${UI_CONST.DURATION_SEC}`;
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    if (m < 60) return `${m} ${UI_CONST.DURATION_MIN} ${s} ${UI_CONST.DURATION_SEC}`;
    const h = Math.floor(m / 60);
    const mm = m % 60;
    return `${h} ${UI_CONST.DURATION_HOUR} ${mm} ${UI_CONST.DURATION_MIN} ${s} ${UI_CONST.DURATION_SEC}`;
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
                label: UI_CONST.CHART_LABEL_MINUTES,
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
                x: { title: { display: true, text: UI_CONST.CHART_X_MINUTES } },
                y: { title: { display: true, text: UI_CONST.CHART_Y_FILES }, beginAtZero: true }
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
                label: UI_CONST.CHART_LABEL_DAYS,
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
                x: { title: { display: true, text: UI_CONST.CHART_X_DAYS } },
                y: { title: { display: true, text: UI_CONST.CHART_Y_FILES }, beginAtZero: true }
            }
        }
    });
}

function renderLogsTable() {
    const tbody = document.querySelector('#logsTable tbody');
    tbody.innerHTML = '';
    if (!logs.length) {
        tbody.innerHTML = `<tr><td colspan="5">${UI_CONST.NO_DATA_TEXT}</td></tr>`;
        return;
    }
    for (const log of logs) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${log.received_at}</td>
            <td>${log.filename}</td>
            <td>${log.duration}</td>
            <td>${log.size}</td>
            <td>
                <button class="open-log-btn" onclick="openLog('${log.filename}','${log.received_at}')">${UI_CONST.OPEN_BTN_LABEL}</button>
                <button class="open-log-btn delete-log-btn" onclick="deleteLog('${log.file_id}')">${UI_CONST.DELETE_BTN_LABEL}</button>
            </td>
        `;
        tbody.appendChild(tr);
    }
}

async function openLog(filename, received_at) {
    const res = await fetch(`/log_text?filename=${encodeURIComponent(filename)}&received_at=${encodeURIComponent(received_at)}`);
    const data = await res.json();
    document.getElementById('logText').textContent = data.text || data.error || UI_CONST.NO_DATA_TEXT;
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

// --- Разделяем обновление графиков и таблицы ---
async function updateCharts() {
    const stats = await fetchStats();
    updateChart(stats);
    const hist = await fetchHistogram();
    updateHistChart(hist);
}

async function refreshTableAndSummary() {
    await fetchLogs();
    await fetchSummary();
}

window.onload = async function() {
    await updateCharts();
    await refreshTableAndSummary();
    setInterval(updateCharts, UI_CONST.UPDATE_INTERVAL_MS); // графики раз в минуту
    setInterval(refreshTableAndSummary, 1000); // таблица и summary раз в секунду
};

// --- Периодическая полная синхронизация с Google Drive ---
async function fullSyncFromServer() {
    await fetchLogs();
    await fetchSummary();
}
setInterval(fullSyncFromServer, 5 * 60 * 1000); // раз в 5 минут

async function deleteLog(file_id) {
    const url = `/log?file_id=${encodeURIComponent(file_id)}`;
    const res = await fetch(url, { method: 'DELETE' });
    const data = await res.json();
    if (data.status === 'deleted') {
        logs = logs.filter(l => l.file_id !== file_id);
        renderLogsTable();
        await fetchSummary();
    } else {
        alert(data.error || UI_CONST.DELETE_ERROR_TEXT);
    }
}
