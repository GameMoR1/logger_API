// settings.js

document.addEventListener('DOMContentLoaded', () => {
    fetch('/api/settings')
        .then(res => res.json())
        .then(data => fillForm(data));

    document.getElementById('settingsForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        document.getElementById('saveStatus').textContent = '';
        document.getElementById('loadingSpinner').style.display = 'flex';
        const modelNames = Array.from(document.querySelectorAll('input[name="modelNames"]:checked')).map(cb => cb.value);
        const payload = {
            modelNames,
            webhookInterval: parseInt(document.getElementById('webhookInterval').value, 10),
            webhookEnabled: document.getElementById('webhookEnabled').checked,
            webhookUrl: document.getElementById('webhookUrl').value,
            loggerApiUrl: document.getElementById('loggerApiUrl').value
        };
        const resp = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        document.getElementById('loadingSpinner').style.display = 'none';
        const status = document.getElementById('saveStatus');
        if (resp.ok) {
            status.textContent = 'Настройки успешно сохранены и отправлены в репозиторий!';
            status.style.color = '#8be9fd';
        } else {
            status.textContent = 'Ошибка сохранения!';
            status.style.color = '#ff5555';
        }
    });

    document.getElementById('fillLoggerUrlBtn').addEventListener('click', () => {
        // Получаем адрес сервера из window.location
        const url = `${window.location.protocol}//${window.location.hostname}:${window.location.port || 80}/log`;
        document.getElementById('loggerApiUrl').value = url;
    });

    document.getElementById('rollbackBtn').addEventListener('click', async () => {
        if (!confirm('Вы уверены, что хотите откатить последние изменения в настройках?')) return;
        document.getElementById('saveStatus').textContent = '';
        document.getElementById('loadingSpinner').style.display = 'flex';
        const resp = await fetch('/api/settings/rollback', { method: 'POST' });
        document.getElementById('loadingSpinner').style.display = 'none';
        const status = document.getElementById('saveStatus');
        if (resp.ok) {
            status.textContent = 'Откат успешно выполнен!';
            status.style.color = '#8be9fd';
            // Перезагрузить форму с откатанными данными
            fetch('/api/settings')
                .then(res => res.json())
                .then(data => fillForm(data));
        } else {
            status.textContent = 'Ошибка отката!';
            status.style.color = '#ff5555';
        }
    });
});

function fillForm(data) {
    // Установить чекбоксы моделей
    const models = data.modelNames || [];
    document.querySelectorAll('input[name="modelNames"]').forEach(cb => {
        cb.checked = models.includes(cb.value);
    });
    document.getElementById('webhookInterval').value = data.webhookInterval || '';
    document.getElementById('webhookEnabled').checked = !!data.webhookEnabled;
    document.getElementById('webhookUrl').value = data.webhookUrl || '';
    document.getElementById('loggerApiUrl').value = data.loggerApiUrl || '';
}
