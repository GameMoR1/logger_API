let chart;
let histChart;
let logs = [];
let allLogs = [];
let currentPage = 1;
const logsPerPage = window.LOGS_PER_PAGE || 10;
let filters = { filename: '', date: '' };
let sortState = { column: null, asc: true };

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
    renderLogsTable(logs);
}

async function fetchSummary() {
    const res = await fetch('/summary');
    const data = await res.json();
    if (!data.error) {
        document.getElementById('totalFiles').textContent = `${UI_CONST.TOTAL_FILES_LABEL}: ${data.total_files}`;
        document.getElementById('totalDuration').textContent = `${UI_CONST.TOTAL_DURATION_LABEL}: ${formatDuration(data.total_duration)}`;
        if (data.total_size !== undefined) {
            document.getElementById('totalSize').textContent = `Общий объем: ${formatFileSize(data.total_size)}`;
        }
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

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Б';
    const k = 1024;
    const dm = 2;
    const sizes = window.SIZE_UNITS || ["Б", "КБ", "МБ", "ГБ", "ТБ"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
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
    if (!chart) {
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
    } else {
        chart.data.labels = labels;
        chart.data.datasets[0].data = values;
        chart.update();
    }
}

function updateHistChart(data) {
    if (!data) return;
    const labels = Object.keys(data).sort();
    const values = labels.map(k => data[k]);
    const ctx = document.getElementById('histChart').getContext('2d');
    if (!histChart) {
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
    } else {
        histChart.data.labels = labels;
        histChart.data.datasets[0].data = values;
        histChart.update();
    }
}

function renderLogsTable(logs) {
    const tbody = document.querySelector('#logsTable tbody');
    tbody.innerHTML = '';
    let sortedLogs = [...logs];
    if (sortState.column) {
        sortedLogs.sort((a, b) => {
            let valA, valB;
            switch (sortState.column) {
                case 'received_at':
                    valA = new Date(a.received_at).getTime();
                    valB = new Date(b.received_at).getTime();
                    break;
                case 'filename':
                    valA = a.filename.toLowerCase();
                    valB = b.filename.toLowerCase();
                    break;
                case 'duration':
                    valA = Number(a.duration);
                    valB = Number(b.duration);
                    break;
                case 'size':
                    valA = Number(a.size);
                    valB = Number(b.size);
                    break;
                default:
                    return 0;
            }
            if (valA < valB) return sortState.asc ? -1 : 1;
            if (valA > valB) return sortState.asc ? 1 : -1;
            return 0;
        });
    }
    const start = (currentPage - 1) * logsPerPage;
    const end = start + logsPerPage;
    const pageLogs = sortedLogs.slice(start, end);
    for (const log of pageLogs) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${formatDateTime(log.received_at)}</td>
            <td>${log.filename}</td>
            <td>${formatDuration(log.duration)}</td>
            <td>${formatFileSize(log.size)}</td>
            <td>
                <button class="open-log-btn" onclick="openLogModal('${log.filename.replace(/'/g, '\'')}', '${log.received_at.replace(/'/g, '\'')}', '${log.file_id || ''}')">Открыть</button>
                <button class="open-log-btn delete-log-btn" onclick="deleteLog('${log.file_id || ''}')">Удалить</button>
            </td>
        `;
        tbody.appendChild(tr);
    }
    renderPagination(logs.length);
}

function openLogModal(filename, received_at, file_id) {
    const modal = document.getElementById('logModal');
    modal.classList.add('loading-modal');
    fetch(`/log_text?filename=${encodeURIComponent(filename)}&received_at=${encodeURIComponent(received_at)}`)
        .then(res => res.json())
        .then(data => {
            let gdocLink = file_id ? `<a href='https://drive.google.com/file/d/${file_id}/view' target='_blank' style='color:#8be9fd;'>Открыть в Google Docs</a><br><br>` : '';
            document.getElementById('logText').innerHTML =
                gdocLink +
                `<div class='log-text-block'><pre style="white-space:pre-wrap;word-break:break-all;margin:0;max-height:600px;overflow:auto;">${data.text ? escapeHtml(data.text) : 'Нет данных'}</pre></div>` +
                `<div style='margin-top:18px;text-align:right;'><button class='open-log-btn delete-log-btn' onclick='deleteLogModal("${file_id}")'>Удалить</button></div>`;
            modal.classList.remove('loading-modal');
            modal.style.display = 'flex';
        });
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}

function closeModal() {
    document.getElementById('logModal').style.display = 'none';
}

// Форматирование даты/времени для таблицы
function formatDateTime(dt) {
    // dt может быть ISO-строкой или timestamp
    const d = new Date(dt);
    if (isNaN(d.getTime())) return dt;
    // Формат: ДД.ММ.ГГГГ HH:MM:SS
    const pad = n => n.toString().padStart(2, '0');
    return `${pad(d.getDate())}.${pad(d.getMonth()+1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function renderPagination(totalLogs) {
    let pages = Math.ceil(totalLogs / logsPerPage);
    const container = document.getElementById('paginationContainer');
    container.innerHTML = '';
    if (pages <= 1) return;

    // Helper to create a page button
    function createPageBtn(i, text = null) {
        const btn = document.createElement('button');
        btn.textContent = text || i;
        btn.className = 'open-log-btn' + (i === currentPage ? ' active' : '');
        btn.onclick = () => {
            if (i !== currentPage && typeof i === 'number') {
                currentPage = i;
                renderLogsTable(logs);
            }
        };
        container.appendChild(btn);
    }

    // Параметры отображения
    const maxVisible = 5; // сколько страниц максимум показывать вокруг текущей
    const showLeft = Math.max(2, currentPage - 2);
    const showRight = Math.min(pages - 1, currentPage + 2);

    // Первая страница
    createPageBtn(1);

    // Троеточие слева
    if (showLeft > 2) {
        createPageBtn(null, '...');
    }

    // Страницы вокруг текущей
    for (let i = showLeft; i <= showRight; i++) {
        if (i > 1 && i < pages) {
            createPageBtn(i);
        }
    }

    // Троеточие справа
    if (showRight < pages - 1) {
        createPageBtn(null, '...');
    }

    // Последняя страница
    if (pages > 1) {
        createPageBtn(pages);
    }
}

function loadLogs() {
    fetch('/logs')
        .then(res => res.json())
        .then(data => {
            allLogs = data;
            logs = data;
            currentPage = 1;
            renderLogsTable(logs);
        });
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
    loadLogs();
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
    // Добавляем обработчики сортировки на заголовки таблицы
    const ths = document.querySelectorAll('#logsTable thead th');
    const columns = ['received_at', 'filename', 'duration', 'size'];
    ths.forEach((th, idx) => {
        if (idx < 4) {
            th.style.cursor = 'pointer';
            th.onclick = () => {
                if (sortState.column === columns[idx]) {
                    sortState.asc = !sortState.asc;
                } else {
                    sortState.column = columns[idx];
                    sortState.asc = true;
                }
                currentPage = 1;
                renderLogsTable(logs);
            };
        }
    });


    // Runpod status fetch
    let lastOnline = null;
    async function updateRunpodStatus() {
        const statusSpan = document.getElementById('runpodStatus');
        const lastOnlineSpan = document.getElementById('runpodLastOnline');
        try {
            statusSpan.textContent = 'Проверка...';
            statusSpan.classList.remove('on', 'off');
            const resp = await fetch('/runpod_status');
            if (resp.ok) {
                const data = await resp.json();
                if (data.status === true) {
                    statusSpan.textContent = 'Включен';
                    statusSpan.classList.add('on');
                    lastOnline = new Date();
                } else {
                    statusSpan.textContent = 'Выключен';
                    statusSpan.classList.add('off');
                }
            } else {
                statusSpan.textContent = 'Выключен';
                statusSpan.classList.add('off');
            }
        } catch (e) {
            statusSpan.textContent = 'Выключен';
            statusSpan.classList.add('off');
        }
        if (lastOnline) {
            lastOnlineSpan.textContent = 'Последний онлайн: ' + formatDateTimeShort(lastOnline);
        } else {
            lastOnlineSpan.textContent = '';
        }
    }
    // Краткий формат даты/времени
    function formatDateTimeShort(dt) {
        const d = new Date(dt);
        if (isNaN(d.getTime())) return '';
        const pad = n => n.toString().padStart(2, '0');
        return `${pad(d.getDate())}.${pad(d.getMonth()+1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    }
    updateRunpodStatus();
    setInterval(updateRunpodStatus, 15000); // обновлять статус каждые 15 секунд

    loadLogs();
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
    const btn = document.querySelector(`button[onclick*="deleteLog('${file_id}'"]`);
    if (btn) btn.classList.add('loading-btn');
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
    if (btn) setTimeout(() => btn.classList.remove('loading-btn'), 400);
}

function deleteLogModal(file_id) {
    if (!file_id) return alert('Нет file_id для удаления!');
    // Анимация удаления
    const modal = document.getElementById('logModal');
    modal.classList.add('loading-modal');
    fetch(`/log?file_id=${encodeURIComponent(file_id)}`, { method: 'DELETE' })
        .then(res => res.json())
        .then(() => {
            setTimeout(() => {
                modal.classList.remove('loading-modal');
                closeModal();
                loadLogs();
            }, 400); // небольшая задержка для анимации
        });
}
