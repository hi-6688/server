// api.js — 後端 API 通訊層
// 統一管理所有前端→後端的 API 呼叫

var BASE_URL = '';
var API_KEY = '';
var CURRENT_INSTANCE = 'main';

export const getCurrentInstance = () => CURRENT_INSTANCE;
export const setCurrentInstance = (id) => { CURRENT_INSTANCE = id; };

// 初始化 API Key
export var initApi = async function () {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const urlKey = urlParams.get('key');

        if (urlKey) {
            API_KEY = urlKey;
        } else {
            // 提供暫時的預設開發用金鑰 (配合 api.py 中的設定)
            API_KEY = 'AdminKey123456';
            console.warn('未在 URL 找到 key 參數，使用預設金鑰');
        }
        console.log('API Key is ready.');
    } catch (e) {
        console.error('API 初始化發生錯誤:', e);
    }
};

// 核心 fetch 工具
var fetchApi = async function (endpoint, method, body) {
    method = method || 'GET';
    body = body || null;

    // 開發環境使用 24445 端口，正式環境使用同源
    var devPort = 24445;
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

// ==================== 實例管理 ====================
export var fetchInstances = function () { return fetchApi('/instances/list'); };
export var createInstance = function (name, port, discordChannelId) {
    return fetchApi('/instances/create', 'POST', { name, port, discord_channel_id: discordChannelId });
};
export var deleteInstance = function (uuid) {
    return fetchApi('/instances/delete', 'POST', { instance_id: uuid });
};


// ==================== 伺服器操作 ====================

// 取得伺服器狀態 (合併 server_status + stats)
export var fetchStatus = async function () {
    try {
        var statusRes = await fetchApi('/server_status');
        var statsRes = await fetchApi('/stats');
        return {
            status: 'success',
            // VM2 虛擬機是否上線 (不管遊戲有沒有開)
            vm2_online: statusRes.vm2_online || false,
            // Minecraft 伺服器是否正在執行
            server_status: statusRes.running ? 'online' : 'offline',
            // 最新浮動 IP
            public_ip: statusRes.public_ip || window.location.hostname,
            stats: {
                cpu: statsRes.cpu?.load_1 || 0,
                mem: statsRes.memory?.percent || 0
            },
            players_online: 0
        };
    } catch (e) {
        return { status: 'error', vm2_online: false };
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

// ==================== 世界與模組的上傳與下載 ====================

// 下載世界
export const downloadWorld = () => {
    var devPort = 24445;
    var origin = (window.location.port === '5173' || window.location.port === '5174')
        ? `${window.location.protocol}//${window.location.hostname}:${devPort}`
        : window.location.origin;
    const url = `${origin}/download?key=${API_KEY}&instance_id=${CURRENT_INSTANCE}`;
    window.open(url, '_blank');
};


const uploadFile = (file, url, onProgress) => {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const formData = new FormData();
        formData.append('file', file);

        xhr.open('POST', url, true);

        xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                onProgress(percentComplete);
            }
        };

        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(JSON.parse(xhr.responseText));
            } else {
                reject(new Error(xhr.statusText));
            }
        };

        xhr.onerror = () => reject(new Error('Network Error'));

        xhr.send(formData);
    });
};

// 上傳世界
export const uploadWorld = (file, onProgress) => {
    var devPort = 24445;
    var origin = (window.location.port === '5173' || window.location.port === '5174')
        ? `${window.location.protocol}//${window.location.hostname}:${devPort}`
        : window.location.origin;
    const url = `${origin}/upload?key=${API_KEY}&instance_id=${CURRENT_INSTANCE}`;
    return uploadFile(file, url, onProgress);
};

// 上傳模組
export const uploadAddon = (file, onProgress) => {
    var devPort = 24445;
    var origin = (window.location.port === '5173' || window.location.port === '5174')
        ? `${window.location.protocol}//${window.location.hostname}:${devPort}`
        : window.location.origin;
    const url = `${origin}/addon/upload?key=${API_KEY}&instance_id=${CURRENT_INSTANCE}`;
    return uploadFile(file, url, onProgress);
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

// ==================== 遊戲規則管理 ====================

// 取得所有遊戲規則 (placeholder)
export const fetchGameRules = () => {
    // In a real scenario, this would be a dedicated endpoint.
    // For now, we simulate it with a command and known rules.
    return Promise.resolve([
        { name: 'commandblockoutput', value: 'true', type: 'boolean' },
        { name: 'dodaylightcycle', value: 'true', type: 'boolean' },
        { name: 'doentitydrops', value: 'true', type: 'boolean' },
        { name: 'dofiretick', value: 'true', type: 'boolean' },
        { name: 'domobloot', value: 'true', type: 'boolean' },
        { name: 'domobspawning', value: 'true', type: 'boolean' },
        { name: 'dotiledrops', value: 'true', type: 'boolean' },
        { name: 'doweathercycle', value: 'true', type: 'boolean' },
        { name: 'drowningdamage', value: 'true', type: 'boolean' },
        { name: 'falldamage', value: 'true', type: 'boolean' },
        { name: 'firedamage', value: 'true', type: 'boolean' },
        { name: 'keepinventory', value: 'false', type: 'boolean' },
        { name: 'mobgriefing', value: 'true', type: 'boolean' },
        { name: 'pvp', value: 'true', type: 'boolean' },
        { name: 'sendcommandfeedback', value: 'true', type: 'boolean' },
        { name: 'showcoordinates', value: 'true', type: 'boolean' },
        { name: 'randomtickspeed', value: '1', type: 'number' },
        { name: 'spawnradius', value: '5', type: 'number' },
        { name: 'maxcommandchainlength', value: '65536', type: 'number' },
        { name: 'functioncommandlimit', value: '10000', type: 'number' },
    ]);
};

// 更新遊戲規則
export const updateGameRule = (rule, value) => {
    return sendCommand(`gamerule ${rule} ${value}`);
};


// ==================== 伺服器資訊 ====================

// 取得伺服器版本
export var fetchVersion = function () { return fetchApi('/version'); };
