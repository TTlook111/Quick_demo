/* 共享工具：Toast / 主题切换 / HTML 转义 / 数据源类型标签 / localStorage 封装 */
// 注意：此文件用经典 <script> 加载（非 module），函数挂到全局供内联 onclick 使用。

// ========== 数据源类型标签 ==========
const TYPE_LABELS = { sqlite: 'SQLite', mysql: 'MySQL', postgresql: 'PostgreSQL' };

// ========== localStorage 封装（两页共享当前会话选中的数据源） ==========
function getSavedDsId() {
    return localStorage.getItem('currentDatasourceId');
}

function setSavedDsId(id) {
    localStorage.setItem('currentDatasourceId', id);
}

// ========== HTML 转义 ==========
function escapeHtml(str) { return String(str ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
function escapeAttr(str) { return String(str ?? '').replace(/'/g, "\\'").replace(/"/g, '&quot;'); }

// ========== Toast 通知 ==========
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    // 3.3 秒后移除（动画 3s + 缓冲）
    setTimeout(() => {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 3300);
}

// ========== 暗色模式 ==========
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);

    const toggle = document.querySelector('.theme-toggle');
    if (toggle) toggle.textContent = next === 'dark' ? '☀️' : '🌙';
}

// 启动时恢复主题
(function() {
    const saved = localStorage.getItem('theme');
    if (saved === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        setTimeout(() => {
            const toggle = document.querySelector('.theme-toggle');
            if (toggle) toggle.textContent = '☀️';
        }, 0);
    }
})();
