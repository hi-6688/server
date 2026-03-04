// api.js — 後端 API 通訊層
// 統一管理所有前端→後端的 API 呼叫

var BASE_URL = '';
var API_KEY = '';
var CURRENT_INSTANCE = 'main';

// 初始化 API Key
export var initApi = async function () {
    try {
        var configUrl = window.location.protocol + '//' + window.location.hostname + ':25564/admin_config.json';
        var res = await fetch(configUrl);
        if (res.ok) {
            var data = await res.json();
            API_KEY = data.apiKey || '';
            console.log('API Key loaded successfully.');
        }
    } catch (e) {
        console.warn('Failed to load API config:', e);
    }
};

// 核心 fetch 工具
var fetchApi = async function (endpoint, method, body) {
    method = method || 'GET';
    body = body || null;

    // 開發環境使用 25564 端口，正式環境使用同源
    var devPort = 25564;
    var origin;
    if (window.location.port === '5173' || window.location.port === '5174') {
        origin = window.location.protocol + '//' + window.location.hostname + ':' + devPort;
    } else {
        origin = window.location.origin;
    }

    var url = new URL(origin + endpoint);
    url.searchParams.append('key', API_KEY);
    url.searchParams.append('instance_id', CURRENT_INSTANCE);

    var options = { method: method };
    if (body) {
        options.headers = { 'Content-Type': 'application/json' };
        options.body = JSON.stringify(Object.assign({}, body, { key: API_KEY, instance_id: CURRENT_INSTANCE }));
    }

    var res = await fetch(url.toString(), options);
    if (!res.ok) throw new Error('HTTP error! status: ' + res.status);
    return await res.json();
};

// ==================== 伺服器操作 ====================

// 取得伺服器狀態 (合併 server_status + stats)
export var fetchStatus = async function () {
    try {
        var statusRes = await fetchApi('/server_status');
        var statsRes = await fetchApi('/stats');
        return {
            status: 'success',
            server_status: statusRes.running ? 'online' : 'offline',
            stats: {
                cpu: statsRes.cpu?.load_1 || 0,
                mem: statsRes.memory?.percent || 0
            },
            players_online: 0
        };
    } catch (e) {
        return { status: 'error' };
    }
};

// 開機/關機
export var sendPowerAction = function (action) { return fetchApi('/' + action, 'POST'); };

// 發送指令
export var sendCommand = function (cmd) { return fetchApi('/command', 'POST', { cmd: cmd }); };
// 相容舊名稱
export var sendCommandToConsole = sendCommand;

// ==================== 檔案讀寫 ====================

// 讀取檔案 (可指定行數)
export var readFile = function (filename, lines) {
    var endpoint = '/read?file=' + encodeURIComponent(filename);
    if (lines) endpoint += '&lines=' + lines;
    return fetchApi(endpoint);
};

// 寫入檔案
export var writeFile = function (filename, content) {
    return fetchApi('/write', 'POST', { file: filename, content: content });
};

// ==================== 世界管理 ====================

// 取得世界清單
export var fetchWorlds = function () { return fetchApi('/worlds'); };

// 切換世界
export var switchWorld = function (worldName) {
    return fetchApi('/switch_world', 'POST', { world: worldName });
};

// 刪除世界
export var deleteWorld = function (worldName) {
    return fetchApi('/delete_world', 'POST', { world: worldName });
};

// ==================== 模組管理 ====================

// 取得模組清單
export var fetchAddons = function () { return fetchApi('/addons'); };

// 刪除模組
export var deleteAddon = function (addonName, addonType) {
    return fetchApi('/addon/delete', 'POST', { name: addonName, type: addonType || 'behavior_packs' });
};

// ==================== 伺服器資訊 ====================

// 取得伺服器版本
export var fetchVersion = function () { return fetchApi('/version'); };
