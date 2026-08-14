/* 聊天查询页逻辑（数据源管理已移至 datasources.html / datasources.js） */

const input = document.getElementById('question');
const resultDiv = document.getElementById('result');
const submitBtn = document.getElementById('submit-btn');
let currentChart = null;
let currentData = null;

// 数据源相关
let datasources = [];
let currentDatasourceId = null;

// 多轮对话上下文
let conversationHistory = [];

// 初始化
loadDatasources();
loadHistory();

// ========== 数据源选择（当前会话使用哪个库） ==========
function getDsName(id) {
    if (id === 'default') return '本地 SQLite（默认）';
    return datasources.find(d => d.id === id)?.name || id;
}

async function loadDatasources() {
    try {
        const res = await fetch('/api/datasources');
        datasources = await res.json();

        const bar = document.getElementById('datasource-bar');
        const select = document.getElementById('datasource-select');

        // 始终显示数据源选择栏
        bar.style.display = 'flex';

        // 默认本地 SQLite 选项 + 自定义数据源
        const options = [{ id: 'default', name: '本地 SQLite（默认）', type: 'sqlite' }].concat(datasources);
        select.innerHTML = options.map(ds =>
            `<option value="${ds.id}">${ds.name}</option>`
        ).join('');

        // 恢复上次选择的数据源
        const saved = getSavedDsId();
        if (saved && options.some(d => d.id === saved)) {
            currentDatasourceId = saved;
            select.value = saved;
        } else {
            currentDatasourceId = options[0].id;
            select.value = options[0].id;
        }
        updateDatasourceBadge();
    } catch (e) {
        console.error('加载数据源失败:', e);
    }
}

function onDatasourceChange() {
    const select = document.getElementById('datasource-select');
    currentDatasourceId = select.value;
    setSavedDsId(currentDatasourceId);
    updateDatasourceBadge();
    // 切换数据源时清除对话上下文
    clearContext();
    showToast(`已切换到: ${getDsName(currentDatasourceId)}`, 'info');
}

function updateDatasourceBadge() {
    const badge = document.getElementById('ds-type-badge');
    let ds = datasources.find(d => d.id === currentDatasourceId);
    if (!ds && currentDatasourceId === 'default') ds = { type: 'sqlite' };
    if (!ds) return;

    badge.textContent = TYPE_LABELS[ds.type] || ds.type;
    badge.className = `ds-type-badge ${ds.type}`;
}

async function refreshSchema() {
    if (!currentDatasourceId) return;
    try {
        const res = await fetch(`/api/datasources/${currentDatasourceId}/refresh-schema`, { method: 'POST' });
        if (res.ok) {
            showToast('Schema 已刷新', 'success');
        } else {
            const err = await res.json();
            showToast(`刷新失败: ${err.detail}`, 'error');
        }
    } catch (e) {
        showToast('刷新请求失败', 'error');
    }
}

input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !submitBtn.disabled) submitQuery();
});

function fillExample(btn) {
    input.value = btn.textContent;
    input.focus();
}

// ========== 多轮对话 ==========
function updateContextBanner() {
    const banner = document.getElementById('context-banner');
    const count = document.getElementById('context-count');
    if (conversationHistory.length > 0) {
        banner.classList.add('visible');
        count.textContent = conversationHistory.length;
    } else {
        banner.classList.remove('visible');
    }
}

function clearContext() {
    conversationHistory = [];
    updateContextBanner();
}

// ========== 历史 ==========
async function loadHistory() {
    try {
        const res = await fetch('/api/history');
        renderHistory(await res.json());
    } catch (e) { console.error(e); }
}

function renderHistory(items) {
    const list = document.getElementById('history-list');
    if (!items || items.length === 0) {
        list.innerHTML = '<div class="history-empty">暂无查询记录</div>';
        return;
    }
    list.innerHTML = items.map(item => `
        <div class="history-item" onclick="rerunQuery('${escapeAttr(item.question)}')">
            <div class="question">${escapeHtml(item.question)}</div>
            <div class="time">${formatTime(item.created_at)}</div>
            <span class="row-count">${item.row_count} 条</span>
            <button class="delete-btn" onclick="event.stopPropagation(); deleteHistoryItem(${item.id})">✕</button>
        </div>
    `).join('');
}

function rerunQuery(question) {
    input.value = question;
    submitQuery();
}

async function deleteHistoryItem(id) {
    await fetch(`/api/history/${id}`, { method: 'DELETE' });
    loadHistory();
}

async function clearAllHistory() {
    if (!confirm('确定清空所有查询历史？')) return;
    await fetch('/api/history', { method: 'DELETE' });
    loadHistory();
}

function formatTime(ts) {
    const diff = Date.now() - ts * 1000;
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
    return new Date(ts * 1000).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// ========== 查询 ==========
async function submitQuery() {
    const question = input.value.trim();
    if (!question) return;

    resultDiv.className = 'result-card visible';
    resultDiv.innerHTML = '<div class="loading"><div class="loading-spinner"></div><div class="loading-text">AI 正在理解问题并生成 SQL...</div></div>';
    submitBtn.disabled = true;

    try {
        const res = await fetch('/api/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question,
                conversation: conversationHistory.length > 0 ? conversationHistory : null,
                datasource_id: currentDatasourceId
            }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || '请求失败');
        }

        currentData = await res.json();
        renderResult(currentData);

        // 加入对话上下文
        conversationHistory.push({ question, sql: currentData.generated_sql });
        if (conversationHistory.length > 5) conversationHistory.shift();
        updateContextBanner();

        loadHistory();
    } catch (e) {
        resultDiv.innerHTML = `<div class="error-block">❌ ${escapeHtml(e.message)}</div>`;
        showToast(e.message, 'error');
    } finally {
        submitBtn.disabled = false;
    }
}

// ========== 渲染结果 ==========
function renderResult(data) {
    const canChart = canShowChart(data);
    let html = '';

    // 自动修复提示
    if (data.auto_fixed) {
        html += `<div class="auto-fix-banner">🔧 原始 SQL 执行失败，AI 已自动修复并重新执行成功</div>`;
        showToast('SQL 已自动修复并执行成功', 'warning');
    }

    // SQL 可编辑区域
    html += `<div class="sql-section">`;
    html += `<div class="section-label">生成的 SQL（可编辑）</div>`;
    html += `<textarea class="sql-editor" id="sql-editor" spellcheck="false">${escapeHtml(data.generated_sql)}</textarea>`;
    html += `<div class="sql-actions">`;
    html += `<button class="run-btn" id="run-edited-btn" onclick="runEditedSQL()">▶ 执行</button><button class="copy-sql-btn" id="copy-sql-btn" onclick="copySQL()">📋 复制</button>`;
    html += `<span class="hint" id="sql-hint">可直接编辑 SQL 后点击执行</span>`;
    html += `</div></div>`;

    // AI 解读区域
    html += `<div id="explain-area"></div>`;

    // 空结果处理
    if (data.row_count === 0) {
        html += `<div class="empty-result">
            <div class="empty-icon">📭</div>
            <div class="empty-title">没有匹配的数据</div>
            <div class="empty-desc">试试换一种方式描述，或者调整查询条件</div>
        </div>`;
        resultDiv.innerHTML = html;
        setupSQLEditor(data.generated_sql);
        return;
    }

    // 工具栏
    html += `<div class="toolbar">`;
    html += `<div class="view-toggle">`;
    html += `<button class="toggle-btn ${canChart ? '' : 'active'}" onclick="switchView('table')">📋 表格</button>`;
    if (canChart) html += `<button class="toggle-btn active" onclick="switchView('chart')">📊 图表</button>`;
    html += `</div>`;
    html += `<div class="export-group">`;
    html += `<button class="export-btn" onclick="exportCSV()">📥 导出 CSV</button>`;
    if (canChart) html += `<button class="export-btn" onclick="exportChartImage()">🖼️ 导出图表</button>`;
    html += `</div>`;
    html += `</div>`;

    if (canChart) {
        html += `<div id="chart-types" class="chart-type-selector">`;
        html += `<button class="chart-type-btn active" onclick="changeChartType('bar')">柱状图</button>`;
        html += `<button class="chart-type-btn" onclick="changeChartType('pie')">饼图</button>`;
        html += `<button class="chart-type-btn" onclick="changeChartType('line')">折线图</button>`;
        html += `<button class="chart-type-btn" onclick="changeChartType('doughnut')">环形图</button>`;
        html += `</div>`;
    }

    html += `<div id="chart-view" style="${canChart ? '' : 'display:none'}"><div class="chart-container"><canvas id="resultChart"></canvas></div></div>`;

    html += `<div id="table-view" style="${canChart ? 'display:none' : ''}">`;
    if (data.rows.length > 0) {
        html += `<div class="table-wrapper"><table class="data-table">`;
        html += `<thead><tr>${data.columns.map(c => `<th class="sortable" onclick="sortTable('${escapeAttr(c)}')">${escapeHtml(c)}</th>`).join('')}</tr></thead>`;
        html += `<tbody>`;
        for (const row of data.rows) {
            html += `<tr>${data.columns.map(c => `<td>${escapeHtml(String(row[c] ?? '-'))}</td>`).join('')}</tr>`;
        }
        html += `</tbody></table></div>`;
    } else {
        html += `<p style="color:#9ca3af;text-align:center;padding:20px;">查询成功，但没有匹配的数据</p>`;
    }
    html += `</div>`;

    html += `<div class="meta"><span class="badge">${data.row_count} 条结果</span></div>`;
    resultDiv.innerHTML = html;

    if (canChart) renderChart(data, 'bar');

    // 绑定 SQL 编辑器事件
    setupSQLEditor(data.generated_sql);

    // 自动触发 AI 解读
    fetchExplanation(data);
}

// ========== 导出 ==========
function exportCSV() {
    if (!currentData || !currentData.rows.length) return;
    const { columns, rows } = currentData;

    let csv = columns.join(',') + '\n';
    for (const row of rows) {
        csv += columns.map(c => {
            const val = String(row[c] ?? '');
            return val.includes(',') ? `"${val}"` : val;
        }).join(',') + '\n';
    }

    downloadFile(csv, 'query_result.csv', 'text/csv');
}

function exportChartImage() {
    if (!currentChart) return;
    const url = currentChart.toBase64Image();
    const a = document.createElement('a');
    a.href = url;
    a.download = 'chart.png';
    a.click();
}

function downloadFile(content, filename, type) {
    const blob = new Blob(['﻿' + content], { type: type + ';charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// ========== 图表 ==========
function switchView(view) {
    document.getElementById('chart-view').style.display = view === 'chart' ? '' : 'none';
    document.getElementById('table-view').style.display = view === 'table' ? '' : 'none';
    const ct = document.getElementById('chart-types');
    if (ct) ct.style.display = view === 'chart' ? 'flex' : 'none';
    document.querySelectorAll('.view-toggle .toggle-btn').forEach((btn, i) => {
        btn.classList.toggle('active', (view === 'table' && i === 0) || (view === 'chart' && i === 1));
    });
}

function canShowChart(data) {
    if (data.rows.length < 2 || data.columns.length < 2) return false;
    return data.columns.some(c => data.rows.every(r => !isNaN(parseFloat(r[c]))));
}

function getChartData(data) {
    const cols = data.columns;
    const numericCols = cols.filter(c => data.rows.every(r => !isNaN(parseFloat(r[c]))));
    const labelCol = cols.find(c => !numericCols.includes(c)) || cols[0];
    const valueCol = numericCols[0] || cols[1];
    return {
        labels: data.rows.map(r => String(r[labelCol])),
        values: data.rows.map(r => parseFloat(r[valueCol])),
        labelCol, valueCol
    };
}

const chartColors = [
    'rgba(79, 70, 229, 0.8)', 'rgba(6, 182, 212, 0.8)', 'rgba(16, 185, 129, 0.8)',
    'rgba(245, 158, 11, 0.8)', 'rgba(239, 68, 68, 0.8)', 'rgba(139, 92, 246, 0.8)',
    'rgba(236, 72, 153, 0.8)', 'rgba(20, 184, 166, 0.8)',
];

function renderChart(data, type) {
    if (currentChart) currentChart.destroy();
    const { labels, values, valueCol } = getChartData(data);
    const canvas = document.getElementById('resultChart');
    if (!canvas) return;
    const isPie = (type === 'pie' || type === 'doughnut');

    currentChart = new Chart(canvas, {
        type,
        data: {
            labels,
            datasets: [{
                label: valueCol,
                data: values,
                backgroundColor: isPie ? labels.map((_, i) => chartColors[i % chartColors.length]) : 'rgba(79, 70, 229, 0.7)',
                borderColor: isPie ? 'white' : 'rgba(79, 70, 229, 1)',
                borderWidth: 2,
                borderRadius: isPie ? 0 : 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: isPie, position: 'bottom', labels: { padding: 14, usePointStyle: true, font: { size: 12 } } },
                tooltip: { backgroundColor: 'rgba(0,0,0,0.8)', padding: 10, cornerRadius: 8 }
            },
            scales: isPie ? {} : {
                x: { grid: { display: false }, ticks: { font: { size: 12 }, color: '#6b7280' } },
                y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.04)' }, ticks: { font: { size: 12 }, color: '#6b7280' } }
            },
            animation: { duration: 500, easing: 'easeOutQuart' }
        }
    });
}

function changeChartType(type) {
    document.querySelectorAll('.chart-type-btn').forEach(btn => {
        btn.classList.toggle('active', btn.textContent.includes(
            type === 'bar' ? '柱状' : type === 'pie' ? '饼图' : type === 'line' ? '折线' : '环形'
        ));
    });
    if (currentData) renderChart(currentData, type);
}

// ========== SQL 可编辑 ==========
let originalSQL = '';

function setupSQLEditor(sql) {
    originalSQL = sql;
    const editor = document.getElementById('sql-editor');
    const hint = document.getElementById('sql-hint');
    if (!editor) return;

    editor.addEventListener('input', () => {
        const modified = editor.value.trim() !== originalSQL.trim();
        editor.classList.toggle('modified', modified);
        if (modified) {
            hint.textContent = '⚠️ SQL 已修改，点击执行查看新结果';
            hint.className = 'hint modified-hint';
        } else {
            hint.textContent = '可直接编辑 SQL 后点击执行';
            hint.className = 'hint';
        }
    });

    // Ctrl+Enter 快捷键执行
    editor.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            runEditedSQL();
        }
    });
}

async function runEditedSQL() {
    const editor = document.getElementById('sql-editor');
    const runBtn = document.getElementById('run-edited-btn');
    if (!editor) return;

    const sql = editor.value.trim();
    if (!sql) return;

    runBtn.disabled = true;
    runBtn.textContent = '执行中...';

    try {
        const res = await fetch('/api/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sql,
                question: currentData?.question || null,
                datasource_id: currentDatasourceId,
            }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || '执行失败');
        }

        currentData = await res.json();
        renderResult(currentData);
        loadHistory();
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        runBtn.disabled = false;
        runBtn.textContent = '▶ 执行';
    }
}

// ========== AI 解读 ==========
async function fetchExplanation(data) {
    const area = document.getElementById('explain-area');
    if (!area || !data.rows.length) return;

    area.innerHTML = `<div class="explain-loading"><span class="dot-pulse">💡</span> AI 正在分析结果...</div>`;

    try {
        const res = await fetch('/api/explain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: data.question,
                sql: data.generated_sql,
                columns: data.columns,
                rows: data.rows,
            }),
        });

        if (!res.ok) throw new Error('解读失败');

        const result = await res.json();
        area.innerHTML = `
            <div class="explain-section">
                <div class="explain-header">🤖 AI 解读</div>
                <div class="explain-text">${escapeHtml(result.explanation)}</div>
            </div>
        `;
    } catch (e) {
        area.innerHTML = '';  // 静默失败，不阻塞主流程
    }
}

// ========== 复制 SQL ==========
function copySQL() {
    const editor = document.getElementById('sql-editor');
    if (!editor) return;

    navigator.clipboard.writeText(editor.value).then(() => {
        const btn = document.getElementById('copy-sql-btn');
        btn.textContent = '✅ 已复制';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.textContent = '📋 复制';
            btn.classList.remove('copied');
        }, 2000);
    }).catch(() => {
        showToast('复制失败', 'error');
    });
}

// ========== 表格排序 ==========
let sortState = { column: null, direction: null };

function sortTable(column) {
    if (!currentData || !currentData.rows.length) return;

    // 切换排序方向
    if (sortState.column === column) {
        sortState.direction = sortState.direction === 'asc' ? 'desc' : 'asc';
    } else {
        sortState.column = column;
        sortState.direction = 'asc';
    }

    // 排序
    const sorted = [...currentData.rows].sort((a, b) => {
        let valA = a[column];
        let valB = b[column];

        // 数字比较
        if (!isNaN(valA) && !isNaN(valB)) {
            valA = Number(valA);
            valB = Number(valB);
        } else {
            valA = String(valA || '');
            valB = String(valB || '');
        }

        if (valA < valB) return sortState.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortState.direction === 'asc' ? 1 : -1;
        return 0;
    });

    // 重新渲染表格体
    const tbody = document.querySelector('.data-table tbody');
    if (!tbody) return;

    tbody.innerHTML = sorted.map(row =>
        `<tr>${currentData.columns.map(c => `<td>${escapeHtml(String(row[c] ?? ''))}</td>`).join('')}</tr>`
    ).join('');

    // 更新表头样式
    document.querySelectorAll('.data-table th.sortable').forEach(th => {
        th.classList.remove('asc', 'desc');
        if (th.textContent === column) {
            th.classList.add(sortState.direction);
        }
    });

    showToast(`按 ${column} ${sortState.direction === 'asc' ? '升序' : '降序'} 排列`, 'info');
}
