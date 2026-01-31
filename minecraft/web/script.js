// 管理面板主程式 - script.js
const API_KEY = "AdminKey123456";
const DAEMON_ID = "d8447ad50fe34eaf9e5f9e2b3a152358";
const INSTANCE_UUID = "92b09a7124084928bcbba4e8f2034513";
const BASE_URL = window.location.origin;
const BACKEND_URL = window.location.protocol + '//' + window.location.hostname + ':24445';

let unifiedPlayers = [];
let PROPERTY_SCHEMA = {};
let currentEditingFile = "";
let originalContent = "";
let parsedProperties = {};

// 載入 Schema
fetch('schema.json').then(r => r.json()).then(data => PROPERTY_SCHEMA = data).catch(e => console.warn('Schema load failed:', e));

// === 區段切換 ===
function showSection(id) {
    document.querySelectorAll('.section').forEach(el => el.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    if (event && event.currentTarget) event.currentTarget.classList.add('active');
    if (id === 'players') loadUnifiedPlayerManager();
    if (id === 'worlds') getWorldSize();
}

// === Shell 指令執行 ===
async function execCmd(cmd) {
    try {
        const res = await fetch(`${BACKEND_URL}/exec?key=${API_KEY}&cmd=${encodeURIComponent(cmd)}`);
        return await res.json();
    } catch (e) { return { error: e.message }; }
}

// === 電源控制 ===
async function power(action) {
    const statusText = document.getElementById('statusText');
    const statusDot = document.querySelector('.status-dot');
    const btn = document.getElementById('powerBtn');

    if (action === 'open') {
        statusText.innerText = "啟動中...";
        const res = await execCmd('systemctl start bedrock');
        if (res.error) { alert('❌ 啟動失敗: ' + res.error); return; }
        setTimeout(() => {
            btn.className = 'btn-power stop';
            btn.innerHTML = '<i class="fas fa-stop"></i>';
            btn.onclick = () => power('stop');
            statusText.innerText = '運行中 (Online)';
            statusDot.className = 'status-dot online';
        }, 2000);
    } else {
        if (!confirm('確定要停止伺服器嗎？')) return;
        statusText.innerText = "停止中...";
        const res = await execCmd('systemctl stop bedrock');
        if (res.error) { alert('❌ 停止失敗: ' + res.error); return; }
        btn.className = 'btn-power';
        btn.innerHTML = '<i class="fas fa-power-off"></i>';
        btn.onclick = () => power('open');
        statusText.innerText = '離線 (Offline)';
        statusDot.className = 'status-dot offline';
    }
}

// === 世界管理 ===
async function getWorldSize() {
    const el = document.getElementById('worldSize');
    if (el) el.innerText = "計算中...";
    try {
        const res = await fetch(`${BACKEND_URL}/size?key=${API_KEY}`);
        if (res.ok) {
            const json = await res.json();
            if (json.size) el.innerText = json.size;
            else el.innerText = "Error";
        } else el.innerText = "N/A";
    } catch (e) { el.innerText = "Timeout"; }
}

async function downloadWorld() {
    document.getElementById('loadingOverlay').style.display = 'block';
    document.getElementById('loadingText').innerText = "壓縮中...";
    const res = await execCmd('zip -r /home/terraria/servers/minecraft/web/world-backup.zip /home/terraria/servers/minecraft/worlds');
    document.getElementById('loadingOverlay').style.display = 'none';
    if (res.error) { alert('❌ 壓縮失敗: ' + res.error); return; }
    window.open(`${window.location.origin}/world-backup.zip`, '_blank');
    alert('✅ 壓縮完成！');
}

async function resetWorld() {
    if (prompt("⚠️ 警告：這會刪除所有世界資料！\n\n請輸入 DELETE 確認重置:") !== "DELETE") return;
    document.getElementById('loadingOverlay').style.display = 'block';
    document.getElementById('loadingText').innerText = "停止伺服器...";
    await execCmd('systemctl stop bedrock');
    document.getElementById('loadingText').innerText = "刪除世界...";
    const res = await execCmd('rm -rf /home/terraria/servers/minecraft/worlds');
    document.getElementById('loadingOverlay').style.display = 'none';
    if (res.error) { alert('❌ 重置失敗: ' + res.error); return; }
    alert('✅ 世界已重置！');
    document.getElementById('statusText').innerText = '離線 (Offline)';
    document.querySelector('.status-dot').className = 'status-dot offline';
}

function triggerUpload() { alert('⚠️ 上傳功能目前無法使用\n請使用 SCP 或 SFTP 上傳檔案到 /home/terraria/servers/minecraft/worlds'); }

// === 玩家管理 ===
async function loadUnifiedPlayerManager() {
    document.getElementById('loadingOverlay').style.display = 'block';
    document.getElementById('loadingText').innerText = "載入玩家資料...";
    try {
        const [allowRes, permRes] = await Promise.all([
            fetch(`${BACKEND_URL}/read?file=allowlist.json&key=${API_KEY}`),
            fetch(`${BACKEND_URL}/read?file=permissions.json&key=${API_KEY}`)
        ]);
        let allowList = [], permList = [];
        if (allowRes.ok) try { allowList = JSON.parse((await allowRes.json()).content) || []; } catch (e) { }
        if (permRes.ok) try { permList = JSON.parse((await permRes.json()).content) || []; } catch (e) { }

        const playerMap = new Map();
        permList.forEach(p => playerMap.set(p.name, { name: p.name, xuid: p.xuid || "", permission: p.permission || "member", whitelisted: false, ignoresLimit: false, online: false }));
        allowList.forEach(p => {
            if (!playerMap.has(p.name)) playerMap.set(p.name, { name: p.name, xuid: p.xuid || "", permission: "member", whitelisted: true, ignoresLimit: p.ignoresPlayerLimit || false, online: false });
            else { const e = playerMap.get(p.name); e.whitelisted = true; e.ignoresLimit = p.ignoresPlayerLimit || false; if (!e.xuid && p.xuid) e.xuid = p.xuid; }
        });
        unifiedPlayers = Array.from(playerMap.values()).sort((a, b) => a.name.localeCompare(b.name));
        renderUnifiedTable();
    } catch (e) { alert("載入失敗: " + e.message); }
    document.getElementById('loadingOverlay').style.display = 'none';
}

function renderUnifiedTable() {
    const container = document.getElementById('unifiedPlayerTable');
    container.innerHTML = '';
    const table = document.createElement('table');
    table.style.cssText = 'width:100%; border-collapse:collapse;';
    table.innerHTML = `<thead><tr style="background:#2d3039; color:#9aa5b1;"><th style="padding:10px;">狀態</th><th style="padding:10px; text-align:left;">名稱</th><th style="padding:10px; text-align:left;">權限</th><th style="padding:10px; text-align:center;">白名單</th><th style="padding:10px; text-align:center;">操作</th></tr></thead><tbody id="unifiedTableBody"></tbody>`;
    const tbody = table.querySelector('tbody');
    unifiedPlayers.forEach((p, idx) => {
        const tr = document.createElement('tr');
        tr.style.cssText = 'border-bottom:1px solid #333;';
        tr.innerHTML = `<td style="padding:10px; text-align:center;"><span style="color:#7f8c8d">● 離線</span></td><td style="padding:10px; font-weight:bold; color:#fff;">${p.name}<div style="font-size:10px; color:#666;">${p.xuid}</div></td><td style="padding:10px;"><select onchange="updatePlayerProp(${idx}, 'permission', this.value)" style="background:#111; border:1px solid #444; color:#fff; padding:5px; border-radius:4px;"><option value="visitor" ${p.permission === 'visitor' ? 'selected' : ''}>訪客</option><option value="member" ${p.permission === 'member' ? 'selected' : ''}>成員</option><option value="operator" ${p.permission === 'operator' ? 'selected' : ''}>管理員</option></select></td><td style="padding:10px; text-align:center;"><input type="checkbox" onchange="updatePlayerProp(${idx}, 'whitelisted', this.checked)" ${p.whitelisted ? 'checked' : ''} style="width:18px; height:18px; cursor:pointer;"></td><td style="padding:10px; text-align:center;"><button onclick="removeUnifiedPlayer(${idx})" style="background:#e74c3c; border:none; color:#fff; padding:5px 10px; border-radius:4px; cursor:pointer;"><i class="fas fa-trash"></i></button></td>`;
        tbody.appendChild(tr);
    });
    container.appendChild(table);
}

async function updatePlayerProp(index, key, value) { unifiedPlayers[index][key] = value; await saveUnifiedManager(true); }

async function addUnifiedPlayer() {
    const name = prompt("請輸入玩家名稱:");
    if (!name) return;
    if (unifiedPlayers.find(p => p.name === name)) { alert("玩家已存在!"); return; }
    unifiedPlayers.push({ name, xuid: "", permission: "member", whitelisted: true, ignoresLimit: false, online: false });
    renderUnifiedTable();
    await saveUnifiedManager(true);
}

async function removeUnifiedPlayer(index) {
    if (confirm("確定移除此玩家?")) { unifiedPlayers.splice(index, 1); renderUnifiedTable(); await saveUnifiedManager(true); }
}

async function saveUnifiedManager(silent = false) {
    const statusLabel = document.getElementById('saveStatus');
    if (!silent) { document.getElementById('loadingOverlay').style.display = 'block'; document.getElementById('loadingText').innerText = "儲存中..."; }
    else if (statusLabel) statusLabel.innerText = "儲存中...";

    const allowlist = unifiedPlayers.filter(p => p.whitelisted).map(p => ({ name: p.name, xuid: p.xuid || undefined, ignoresPlayerLimit: p.ignoresLimit }));
    const permissions = unifiedPlayers.map(p => ({ name: p.name, xuid: p.xuid || undefined, permission: p.permission }));

    try {
        await fetch(`${BACKEND_URL}/write`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: API_KEY, file: 'allowlist.json', content: JSON.stringify(allowlist, null, 2) }) });
        await fetch(`${BACKEND_URL}/write`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: API_KEY, file: 'permissions.json', content: JSON.stringify(permissions, null, 2) }) });
        if (!silent) alert("✅ 儲存成功!");
        else if (statusLabel) { statusLabel.innerText = "已儲存"; setTimeout(() => statusLabel.innerText = "", 2000); }
    } catch (e) { if (!silent) alert("儲存失敗: " + e.message); }
    document.getElementById('loadingOverlay').style.display = 'none';
}

// === 設定編輯器 ===
async function openConfig(filename) {
    currentEditingFile = filename;
    document.getElementById('loadingOverlay').style.display = 'block';
    document.getElementById('loadingText').innerText = "讀取設定中...";
    try {
        const res = await fetch(`${BACKEND_URL}/read?file=${filename}&key=${API_KEY}`);
        if (res.status !== 200) throw new Error((await res.json()).error || "Fetch failed");
        const data = await res.json();
        originalContent = data.content;
        if (filename === 'server.properties') renderPropertiesForm(data.content);
        else renderRawEditor(data.content);
        document.getElementById('editorTitle').innerText = "編輯: " + filename;
        document.getElementById('editorModal').style.display = 'block';
    } catch (e) { alert("錯誤: " + e.message); }
    document.getElementById('loadingOverlay').style.display = 'none';
}

function parseProperties(content) {
    const props = {};
    content.split('\n').forEach(line => {
        line = line.trim();
        if (!line || line.startsWith('#')) return;
        const idx = line.indexOf('=');
        if (idx > 0) props[line.substring(0, idx).trim()] = line.substring(idx + 1).trim();
    });
    return props;
}

function renderPropertiesForm(content) {
    parsedProperties = parseProperties(content);
    const formDiv = document.getElementById('editorForm');
    const rawArea = document.getElementById('editorArea');
    formDiv.style.display = 'grid';
    rawArea.style.display = 'none';
    formDiv.innerHTML = '';

    for (const [key, schema] of Object.entries(PROPERTY_SCHEMA)) {
        const val = parsedProperties[key] || '';
        const wrapper = document.createElement('div');
        wrapper.className = 'form-group';
        const label = document.createElement('label');
        label.innerText = schema.label || key;
        wrapper.appendChild(label);
        if (schema.desc) { const desc = document.createElement('small'); desc.style.cssText = 'color:#666; font-size:11px;'; desc.innerText = schema.desc; wrapper.appendChild(desc); }

        let input;
        if (schema.type === 'boolean') {
            input = document.createElement('div');
            input.className = val === 'true' ? 'toggle-switch checked' : 'toggle-switch';
            input.onclick = function () { this.classList.toggle('checked'); this.dataset.value = this.classList.contains('checked') ? 'true' : 'false'; };
            input.dataset.value = val;
            input.appendChild(document.createElement('span'));
        } else if (schema.type === 'select') {
            input = document.createElement('select');
            schema.options.forEach(opt => { const o = document.createElement('option'); o.value = opt; o.innerText = opt; if (val === opt) o.selected = true; input.appendChild(o); });
        } else {
            input = document.createElement('input');
            input.type = schema.type === 'number' ? 'number' : 'text';
            input.value = val;
        }
        input.dataset.key = key;
        wrapper.appendChild(input);
        formDiv.appendChild(wrapper);
    }
}

function renderRawEditor(content) {
    document.getElementById('editorForm').style.display = 'none';
    document.getElementById('editorArea').style.display = 'block';
    document.getElementById('editorArea').value = content;
}

async function saveConfig() {
    let finalContent = "";
    if (currentEditingFile === 'server.properties') {
        const lines = originalContent.split('\n');
        const inputs = document.querySelectorAll('#editorForm [data-key]');
        const newValues = {};
        inputs.forEach(el => { newValues[el.dataset.key] = el.classList.contains('toggle-switch') ? el.dataset.value || 'false' : el.value; });
        finalContent = lines.map(line => {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith('#')) return line;
            const idx = line.indexOf('=');
            if (idx === -1) return line;
            const key = line.substring(0, idx).trim();
            return newValues.hasOwnProperty(key) ? `${key}=${newValues[key]}` : line;
        }).join('\n');
    } else {
        finalContent = document.getElementById('editorArea').value;
    }

    document.getElementById('loadingOverlay').style.display = 'block';
    document.getElementById('loadingText').innerText = "儲存中...";
    try {
        const res = await fetch(`${BACKEND_URL}/write`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: API_KEY, file: currentEditingFile, content: finalContent }) });
        if (res.status !== 200) throw new Error((await res.json()).error || "Save failed");
        document.getElementById('editorModal').style.display = 'none';
        alert("✅ 設定已更新! 請重啟伺服器套用。");
    } catch (e) { alert("儲存失敗: " + e.message); }
    document.getElementById('loadingOverlay').style.display = 'none';
}

function closeEditor() { document.getElementById('editorModal').style.display = 'none'; }
