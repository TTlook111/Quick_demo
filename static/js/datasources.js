/* 数据源管理页逻辑（列表 / 使用 / 测试 / 刷新 / 删除 / 添加） */

let datasources = [];
// 当前会话选中的数据源（与聊天页通过 localStorage 共享）
let currentDatasourceId = getSavedDsId() || 'default';

// 初始化
loadDsList();
onDsTypeChange();

// ========== 数据源列表 ==========
async function loadDsList() {
    try {
        const res = await fetch('/api/datasources');
        datasources = await res.json();
        renderDsList();
    } catch (e) {
        console.error('加载数据源失败:', e);
        document.getElementById('ds-list').innerHTML = '<div class="ds-list-empty">加载失败，请刷新重试</div>';
    }
}

function renderDsList() {
    const list = document.getElementById('ds-list');
    if (!datasources.length) {
        list.innerHTML = '<div class="ds-list-empty">还没有自定义数据源，使用下方表单添加</div>';
        return;
    }

    list.innerHTML = datasources.map(ds => {
        const detail = ds.type === 'sqlite'
            ? (ds.database || '默认文件 demo.db')
            : `${ds.host || '-'}:${ds.port || '-'} / ${ds.database || '-'}（${ds.username || '无账号'}）`;
        const isCurrent = currentDatasourceId === ds.id;
        return `
            <div class="ds-list-item">
                <div class="ds-item-info">
                    <span class="ds-item-name">${escapeHtml(ds.name)}</span>
                    <span class="ds-type-badge ${ds.type}">${TYPE_LABELS[ds.type] || ds.type}</span>
                    <span class="ds-item-detail" title="${escapeAttr(detail)}">${escapeHtml(detail)}</span>
                </div>
                <div class="ds-item-actions">
                    ${isCurrent
                        ? '<span class="ds-current">当前使用</span>'
                        : `<button class="ds-use-btn" onclick="useDs('${ds.id}')">使用</button>`}
                    <button class="ds-act-btn" onclick="testSavedDs('${ds.id}')">测试</button>
                    <button class="ds-act-btn" onclick="refreshDsSchema('${ds.id}')">刷新</button>
                    <button class="ds-del-btn" onclick="deleteDs('${ds.id}')">删除</button>
                </div>
            </div>`;
    }).join('');
}

// 使用该数据源：设为当前会话的库并返回聊天页
function useDs(id) {
    setSavedDsId(id);
    currentDatasourceId = id;
    showToast(`已切换到: ${datasources.find(d => d.id === id)?.name || id}`, 'success');
    setTimeout(() => { location.href = '/'; }, 300);
}

// 测试已保存的数据源
async function testSavedDs(id) {
    try {
        const res = await fetch(`/api/datasources/${id}/test`, { method: 'POST' });
        if (res.ok) {
            const r = await res.json();
            showToast('✅ ' + r.message, 'success');
        } else {
            const err = await res.json();
            showToast('❌ ' + (err.detail || '连接失败'), 'error');
        }
    } catch (e) {
        showToast('❌ 测试请求失败', 'error');
    }
}

// 刷新数据源 Schema
async function refreshDsSchema(id) {
    try {
        const res = await fetch(`/api/datasources/${id}/refresh-schema`, { method: 'POST' });
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

// 删除数据源
async function deleteDs(id) {
    const ds = datasources.find(d => d.id === id);
    if (!confirm(`确定删除数据源「${ds?.name || id}」？`)) return;
    try {
        const res = await fetch(`/api/datasources/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('删除失败');
        showToast('已删除', 'success');
        if (currentDatasourceId === id) {
            currentDatasourceId = 'default';
            setSavedDsId('default');
        }
        await loadDsList();
    } catch (e) {
        showToast('删除失败', 'error');
    }
}

// ========== 添加数据源表单 ==========
function onDsTypeChange() {
    const type = document.getElementById('ds-type').value;
    const isServer = type !== 'sqlite';
    // SQLite 不需要主机/端口/账号密码
    document.querySelectorAll('.ds-form [data-server]').forEach(row => {
        row.style.display = isServer ? '' : 'none';
    });
    const dbInput = document.getElementById('ds-database');
    dbInput.placeholder = isServer
        ? '数据库名称（如 mydb）'
        : 'SQLite 文件路径（如 mydata.db，留空用默认 demo.db）';
    setDsFormStatus('', true);
}

function collectDsForm() {
    const portVal = document.getElementById('ds-port').value;
    return {
        name: document.getElementById('ds-name').value.trim(),
        type: document.getElementById('ds-type').value,
        host: document.getElementById('ds-host').value.trim(),
        port: portVal ? parseInt(portVal, 10) : null,
        username: document.getElementById('ds-username').value.trim(),
        password: document.getElementById('ds-password').value,
        database: document.getElementById('ds-database').value.trim(),
    };
}

function setDsFormStatus(msg, ok = true) {
    const el = document.getElementById('ds-form-status');
    el.textContent = msg;
    el.className = 'ds-form-status ' + (ok ? 'ok' : 'err');
}

// 保存前测试连接配置
async function testDsConnection() {
    const payload = collectDsForm();
    const btn = document.getElementById('ds-test-btn');
    btn.disabled = true;
    btn.textContent = '测试中...';
    setDsFormStatus('正在测试连接...', true);
    try {
        const res = await fetch('/api/datasources/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (res.ok) {
            const r = await res.json();
            setDsFormStatus('✅ ' + r.message, true);
        } else {
            const err = await res.json();
            setDsFormStatus('❌ ' + (err.detail || '连接失败'), false);
        }
    } catch (e) {
        setDsFormStatus('❌ 测试请求失败', false);
    } finally {
        btn.disabled = false;
        btn.textContent = '🔌 测试连接';
    }
}

// 保存新数据源：成功后设为当前会话的库并返回聊天页
async function saveDs() {
    const payload = collectDsForm();
    if (!payload.name) { setDsFormStatus('请填写显示名称', false); return; }
    if (payload.type !== 'sqlite' && !payload.database) { setDsFormStatus('请填写数据库名', false); return; }

    const btn = document.getElementById('ds-save-btn');
    btn.disabled = true;
    btn.textContent = '保存中...';
    try {
        const res = await fetch('/api/datasources', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (res.ok) {
            const r = await res.json();
            showToast('✅ 数据源添加成功', 'success');
            setSavedDsId(r.id);
            currentDatasourceId = r.id;
            setTimeout(() => { location.href = '/'; }, 400);
        } else {
            const err = await res.json();
            setDsFormStatus('❌ ' + (err.detail || '添加失败'), false);
        }
    } catch (e) {
        setDsFormStatus('❌ 保存请求失败', false);
    } finally {
        btn.disabled = false;
        btn.textContent = '💾 保存';
    }
}

// 返回聊天页
function backToChat() {
    location.href = '/';
}
