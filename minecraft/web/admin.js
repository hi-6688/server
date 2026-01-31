// Global Configuration Variables
let API_KEY = "";
let DAEMON_ID = "";
let INSTANCE_UUID = "";
let BASE_URL = window.location.origin;

// Determine Backend URL
let BACKEND_URL = "";
if (window.location.protocol === 'file:') {
    BACKEND_URL = "http://localhost:24445"; // Default for local file access
} else {
    // Check if we are potentially behind a proxy or just standard access
    // Use relative path to let browser handle origin
    BACKEND_URL = "";
}

// Initialize Logic
const DataManager = {
    // State
    intervals: [],
    lastEditTimes: { players: 0, rules: 0, props: 0 },

    // UI Helpers
    setLoading(id, isLoading) {
        const container = document.getElementById(id);
        if (!container) return;
        if (isLoading) {
            if (!container.querySelector('.loading-spinner')) {
                container.innerHTML = '<div class="loading-spinner" style="text-align:center; padding:20px; color:#aaa;"><i class="fas fa-spinner fa-spin"></i> 載入中...</div>';
            }
        }
    },
    setError(id, msg) {
        const container = document.getElementById(id);
        if (!container) return;
        container.innerHTML = `<div style="text-align:center; padding:20px; color:#e74c3c;"><i class="fas fa-exclamation-triangle"></i> 載入失敗: ${msg}</div>`;
    },

    // Initialization
    async init() {
        try {
            const res = await fetch('admin_config.json');
            const config = await res.json();
            API_KEY = config.apiKey;
            DAEMON_ID = config.daemonId;
            INSTANCE_UUID = config.instanceUuid;
            if (config.backendUrl) BACKEND_URL = config.backendUrl;

            console.log("Config Loaded. Backend:", BACKEND_URL);

            // Initial Fetches
            this.refreshAll(false); // First load with spinners

            // Start Master Sync Loop (Every 5 seconds)
            this.startAutoSync();

        } catch (e) {
            console.error("Init failed:", e);
            alert("Fatal Error: Failed to load admin config.");
        }
    },

    startAutoSync() {
        // Clear existing
        this.intervals.forEach(clearInterval);
        this.intervals = [];

        // Master Loop (5s)
        const id = setInterval(() => this.refreshAll(true), 5000);
        this.intervals.push(id);
        console.log("Auto-Sync Started (PID " + id + ")");
    },

    async refreshAll(silent = true) {
        // 如果使用者正在輸入，跳過刷新以避免打斷
        const activeEl = document.activeElement;
        const isUserTyping = activeEl && (
            activeEl.tagName === 'INPUT' ||
            activeEl.tagName === 'TEXTAREA' ||
            activeEl.tagName === 'SELECT' ||
            activeEl.isContentEditable
        );

        if (isUserTyping && silent) {
            // 使用者正在輸入，只更新狀態欄 (不影響表單)
            await updateServerStatus();
            return;
        }

        const activeSection = document.querySelector('.section.active') ? document.querySelector('.section.active').id : 'dashboard';

        const tasks = [
            updateServerStatus(), // Always check status
            getVersion() // Always check version
        ];

        // Section-specific data refresh
        if (activeSection === 'players') tasks.push(loadUnifiedPlayerManager(silent));
        if (activeSection === 'gamerules') tasks.push(loadGameRules(silent));
        if (activeSection === 'options') {
            tasks.push(loadInlineServerProperties(silent));
            tasks.push(loadWebConfig());
        }
        if (activeSection === 'worlds') {
            tasks.push(getWorldSize());
            tasks.push(loadAddons(silent));
        }

        // Always check system stats on dashboard
        if (activeSection === 'dashboard') tasks.push(updateSystemStats());

        await Promise.allSettled(tasks);
    }
};

// Start
document.addEventListener('DOMContentLoaded', () => {
    try {
        checkAuth();
    } catch (e) {
        console.error("Auth Check Failed:", e);
        // Fallback: Ensure login is shown
        document.getElementById('loginModal').style.display = 'flex';
    }
});

// =============================================================================
// [SECTION 0] SYSTEM STATISTICS
// =============================================================================
async function updateSystemStats() {
    try {
        const res = await fetch(`${BACKEND_URL}/stats?key=${API_KEY}`);
        if (!res.ok) return;
        const data = await res.json();

        // 1. CPU
        if (data.cpu) {
            document.getElementById('cpuLoad').innerText = `${data.cpu.load_1.toFixed(2)} / ${data.cpu.load_5.toFixed(2)}`;
        }

        // 2. RAM
        if (data.memory) {
            document.getElementById('ramPercent').innerText = data.memory.percent + '%';
            document.getElementById('ramUsed').innerText = data.memory.used.replace('GB', 'G').replace('MB', 'M');
            document.getElementById('ramTotal').innerText = data.memory.total.replace('GB', 'G').replace('MB', 'M');
            document.getElementById('ramBar').style.width = data.memory.percent + '%';
        }

        // 3. Disk
        if (data.disk) {
            document.getElementById('diskPercent').innerText = data.disk.percent + '%';
            document.getElementById('diskUsed').innerText = data.disk.used.replace('GB', 'G');
            document.getElementById('diskTotal').innerText = data.disk.total.replace('GB', 'G');
            document.getElementById('diskBar').style.width = data.disk.percent + '%';
        }

        // 4. Network
        if (data.network) {
            document.getElementById('netRx').innerText = data.network.rx_gb.replace('GB', 'G'); // e.g. 24.12 G
            document.getElementById('netTx').innerText = data.network.tx_gb.replace('GB', 'G');
        }

    } catch (e) {
        console.warn("Stats update failed", e);
    }
}

function checkAuth() {
    // Ensure loading overlay is hidden so it doesn't block interaction
    const loader = document.getElementById('loadingOverlay');
    if (loader) loader.style.display = 'none';

    try {
        const sessionKey = localStorage.getItem('admin_api_key');
        if (sessionKey) {
            // Already logged in
            document.getElementById('loginModal').style.display = 'none';
            DataManager.init();
        } else {
            // Show login
            const modal = document.getElementById('loginModal');
            modal.style.display = 'flex';

            // Auto-focus input
            setTimeout(() => {
                const input = document.getElementById('loginPassword');
                if (input) {
                    input.focus();
                    input.click(); // Mobile compat
                }
            }, 100);
        }
    } catch (e) {
        // In case localStorage is restricted
        console.warn("Storage access failed, defaulting to login prompt", e);
        document.getElementById('loginModal').style.display = 'flex';
    }
}

// Make doLogin globally available
window.doLogin = doLogin;

async function doLogin() {
    console.log("doLogin called");
    const pwdInput = document.getElementById('loginPassword');
    const errDisplay = document.getElementById('loginError');
    const pwd = pwdInput.value;

    if (!pwd) return;

    // UI Loading state
    const btn = document.querySelector('#loginModal button');
    const originalText = btn.innerText;
    btn.innerText = 'Verifying...';
    btn.disabled = true;

    try {
        const res = await fetch(BACKEND_URL + '/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: pwd })
        });

        if (res.ok) {
            const data = await res.json();
            if (data.status === 'ok') {
                // Success
                localStorage.setItem('admin_api_key', data.key);
                document.getElementById('loginModal').style.display = 'none';
                DataManager.init();
            } else {
                errDisplay.innerText = data.error || 'Login failed';
                errDisplay.style.display = 'block';
            }
        } else {
            errDisplay.innerText = '密碼錯誤 (Invalid Password)';
            errDisplay.style.display = 'block';
        }
    } catch (e) {
        errDisplay.innerText = 'Connection Error: ' + e.message;
        errDisplay.style.display = 'block';
    }

    btn.innerText = originalText;
    btn.disabled = false;
}

// =============================================================================
// [SECTION 1] SERVER STATUS & POWER MANAGEMENT
// =============================================================================
async function updateServerStatus() {
    try {
        // 1. Check if process is running (Fast & Reliable)
        const statusRes = await fetch(`${BACKEND_URL}/server_status?key=${API_KEY}`);
        if (!statusRes.ok) throw new Error("Status API Check Failed");
        const statusData = await statusRes.json();

        const statusText = document.getElementById('statusText');
        const statusDot = document.querySelector('.status-dot');
        const countDisplay = document.getElementById('playerCountDisplay');
        const btn = document.getElementById('powerBtn');

        if (statusData.running) {
            // Online
            statusText.innerText = '運行中 (Online)';
            statusDot.className = 'status-dot online';
            btn.className = 'btn-power rounded-rect stop';
            btn.innerHTML = '<i class="fas fa-stop"></i><span style="font-size:14px; margin-left:8px;">停止</span>';
            btn.onclick = () => power('stop');

            // 2. Refresh Player Count (via list command)
            // We do this AFTER updating status so UI feels snappy
            runCmd('list').then(async (listRes) => {
                if (listRes.ok) {
                    const result = (await listRes.json()).result || "";
                    // Regex: Match "There are X/Y players" globally
                    const matches = [...result.matchAll(/There are\s+(\d+\/\d+)\s+players/g)];

                    if (matches.length > 0) {
                        // Get the last match (most recent)
                        const lastMatch = matches[matches.length - 1];
                        countDisplay.innerText = lastMatch[1];
                    } else {
                        // Regex failed, but server is running. Default to 0 / 10
                        countDisplay.innerText = "0 / 10";
                    }
                }
            }).catch(() => {
                // Ignore list failure if status is verified running
                countDisplay.innerText = "? / ?";
            });

        } else {
            throw new Error("Offline");
        }
    } catch (e) {
        // Offline
        document.getElementById('statusText').innerText = '離線 (Offline)';
        document.querySelector('.status-dot').className = 'status-dot offline';
        document.getElementById('playerCountDisplay').innerText = '- / -';

        const btn = document.getElementById('powerBtn');
        btn.className = 'btn-power rounded-rect';
        btn.innerHTML = '<i class="fas fa-power-off"></i><span style="font-size:14px; margin-left:8px;">啟動</span>';
        btn.onclick = () => power('open');
    }
}

// 取得伺服器版本
async function getVersion() {
    try {
        const res = await fetch(`${BACKEND_URL}/version?key=${API_KEY}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const versionEl = document.getElementById('versionDisplay');
        if (versionEl) versionEl.innerText = data.version || "Unknown";
    } catch (e) {
        console.error("Failed to get version:", e);
        const versionEl = document.getElementById('versionDisplay');
        if (versionEl) versionEl.innerText = "Unknown";
    }
}

async function power(action) {
    const statusText = document.getElementById('statusText');
    if (action === 'open') {
        statusText.innerText = "啟動中...";
        // Use screen to start
        const cmd = 'screen -dmS bedrock -L -Logfile bedrock_screen.log bash -c "LD_LIBRARY_PATH=. ./bedrock_server; exec bash"';
        const res = await execCmd(cmd);
        if (res.returncode !== 0 && res.error) alert('❌ 啟動失敗: ' + (res.error || res.output));
        setTimeout(updateServerStatus, 3000);
    } else if (action === 'restart') {
        if (!confirm('確定要重新啟動伺服器嗎？')) return;
        statusText.innerText = "重啟中...";
        // Restart = Stop + Start (Screen doesn't handle restart gracefully, so we sequence it)
        await execCmd('screen -S bedrock -X quit');
        setTimeout(async () => {
            const cmd = 'screen -dmS bedrock -L -Logfile bedrock_screen.log bash -c "LD_LIBRARY_PATH=. ./bedrock_server; exec bash"';
            await execCmd(cmd);
            setTimeout(updateServerStatus, 3000);
        }, 3000);
    } else {
        if (!confirm('確定要停止伺服器嗎？')) return;
        statusText.innerText = "停止中...";
        const res = await execCmd('screen -S bedrock -X quit');
        if (res.returncode !== 0 && res.error) alert('❌ 停止失敗: ' + (res.error || res.output));
        setTimeout(updateServerStatus, 2000);
    }
}
function copyText(text) {
    navigator.clipboard.writeText(text).then(() => {
        // Silent success
    }).catch(err => {
        console.error('Async: Could not copy text: ', err);
    });
}

// =============================================================================
// [SECTION 2] UNIFIED PLAYER MANAGER
// Manages Allowlist, Permissions, and Online Players in a single table.
// =============================================================================
let unifiedPlayers = [];

// Global debounce timestamp
let lastPlayerEditTime = 0;

async function loadUnifiedPlayerManager(silent = false) {
    // If user edited recently (within 4 seconds), skip refresh
    if (Date.now() - lastPlayerEditTime < 4000) return;

    const containerId = 'unifiedPlayerTable';
    if (!silent) DataManager.setLoading(containerId, true);

    try {
        const [allowRes, permRes, listRes, logRes] = await Promise.all([
            fetch(`${BACKEND_URL}/read?key=${API_KEY}&file=allowlist.json`),
            fetch(`${BACKEND_URL}/read?key=${API_KEY}&file=permissions.json`),
            fetch(`${BACKEND_URL}/command?key=${API_KEY}&cmd=list`),
            fetch(`${BACKEND_URL}/read?key=${API_KEY}&file=bedrock_screen.log&lines=3000`)
        ]);

        if (Date.now() - lastPlayerEditTime < 4000) return;

        const allowText = (await allowRes.json()).content || "[]";
        const permText = (await permRes.json()).content || "[]";
        const logText = logRes.ok ? (await logRes.json()).content || "" : "";

        let allowList = [];
        let permList = [];
        try { allowList = JSON.parse(allowText); } catch (e) { }
        try { permList = JSON.parse(permText); } catch (e) { }

        // Define flag for auto-save if we discover new players with valid XUIDs
        let shouldSave = false;

        // Parse XUIDs from log
        const nameToXuid = new Map();
        const xuidToName = new Map();
        if (logText) {
            const lines = logText.split('\n');
            const connectRegex = /Player connected: (.+?), xuid: (\d+)/;
            const spawnRegex = /Player Spawned: (.+?) xuid: (\d+)/;

            lines.forEach(line => {
                let match = line.match(connectRegex);
                if (match) {
                    nameToXuid.set(match[1].trim(), match[2]);
                    xuidToName.set(match[2], match[1].trim());
                } else {
                    match = line.match(spawnRegex);
                    if (match) {
                        nameToXuid.set(match[1].trim(), match[2]);
                        xuidToName.set(match[2], match[1].trim());
                    }
                }
            });
        }

        let onlineNames = new Set();
        if (listRes.ok) {
            const listText = (await listRes.json()).result || "";
            // Update Player Count (Handle log timestamp prefix)
            const match = listText.match(/There are (\d+)\/(\d+) players/);
            if (match && match[1]) {
                document.getElementById('playerCountDisplay').innerText = `${match[1]} / ${match[2]}`;
            }

            const lines = listText.split('\n');
            // Find the *last* occurrence of the status line to ensure we use the latest command output
            let statusLineIndex = -1;
            let onlineCount = 0;

            for (let i = lines.length - 1; i >= 0; i--) {
                const match = lines[i].match(/There are (\d+)\/(\d+) players/);
                if (match) {
                    statusLineIndex = i;
                    onlineCount = parseInt(match[1]);
                    if (match[1]) {
                        document.getElementById('playerCountDisplay').innerText = `${match[1]} / ${match[2]}`;
                    }
                    break;
                }
            }

            // If we found a status line and count is 0, we can safely ignore everything else
            // This prevents "Level Name: ...", "Version: ..." from being parsed as players on startup
            if (statusLineIndex !== -1 && onlineCount === 0) {
                onlineNames.clear(); // Ensure empty
            } else if (statusLineIndex !== -1) {
                // Determine start index (usually lines after status line)
                // We scan lines *after* the status line
                for (let i = statusLineIndex + 1; i < lines.length; i++) {
                    const line = lines[i];
                    if (line.includes('list')) continue;
                    if (!line.trim()) continue;

                    const parts = line.split('INFO]');
                    const content = parts.length > 1 ? parts[1].trim() : line.trim();

                    if (!content || content.startsWith('[')) continue;

                    // Strict Garbage Filter
                    // Exclude common server startup log messages that might appear
                    const garbage = ['Level Name:', 'Version:', 'Session ID:', 'Build ID:', 'Branch:', 'Commit ID:', 'Configuration:', 'Game mode:', 'Difficulty:', 'IPv4', 'IPv6', 'Server started', 'opening level', 'Pack Stack', 'No CDN', 'Content logging'];
                    if (garbage.some(g => content.includes(g))) continue;
                    if (content.includes('=')) continue; // Config lines

                    const names = content.split(',');
                    names.forEach(n => {
                        const cleanName = n.trim();
                        if (cleanName && cleanName !== 'There are' && !cleanName.includes('players online')) {
                            // Extra check: Player names usually don't have colons (unless strange gamertag)
                            // System messages often do.
                            if (cleanName.includes(':')) return;
                            if (cleanName.includes('"') || cleanName.startsWith('op ') || cleanName.startsWith('deop ')) return;
                            onlineNames.add(cleanName);
                        }
                    });
                }
            }
            // Fallback: If no status line found (rare), preserve existing or do nothing
            // (Current logic effectively cleared it implicitly by recreating Set, but we want to be safe)
        }

        const playerMap = new Map();

        permList.forEach(p => {
            // Update XUID from log if missing
            const xuid = p.xuid || nameToXuid.get(p.name) || "";
            // Recover name if missing
            const name = p.name || xuidToName.get(xuid) || (xuid ? `User-${xuid.substr(0, 4)}` : "Unknown");

            playerMap.set(name, { name: name, xuid: xuid, permission: p.permission || "member", whitelisted: false, ignoresLimit: false, online: false });
        });

        allowList.forEach(p => {
            if (!playerMap.has(p.name)) {
                // Update XUID from log if missing
                const xuid = p.xuid || nameToXuid.get(p.name) || "";
                playerMap.set(p.name, { name: p.name, xuid: xuid, permission: "member", whitelisted: true, ignoresLimit: p.ignoresPlayerLimit || false, online: false });
            } else {
                const existing = playerMap.get(p.name);
                existing.whitelisted = true;
                existing.ignoresLimit = p.ignoresPlayerLimit || false;
                if (!existing.xuid && (p.xuid || nameToXuid.get(p.name))) {
                    existing.xuid = p.xuid || nameToXuid.get(p.name);
                }
            }
        });

        onlineNames.forEach((name) => {
            if (!playerMap.has(name)) {
                // Try to find XUID from log
                const xuid = nameToXuid.get(name) || "";
                playerMap.set(name, { name: name, xuid: xuid, permission: "member", whitelisted: false, ignoresLimit: false, online: true });

                // [NEW] 如果抓到新玩家且有 XUID，自動保存以達成「路人留存」
                // Only save if we actually have an XUID, otherwise permissions.json won't accept it anyway
                if (xuid) {
                    shouldSave = true;
                }
            } else {
                const p = playerMap.get(name);
                p.online = true;
                // Double check XUID update
                if (!p.xuid && nameToXuid.get(name)) {
                    p.xuid = nameToXuid.get(name);
                    shouldSave = true; // XUID updated, sync to file
                }
            }
        });

        unifiedPlayers = Array.from(playerMap.values()).sort((a, b) => {
            if (a.online && !b.online) return -1;
            if (!a.online && b.online) return 1;
            return a.name.localeCompare(b.name);
        });

        renderUnifiedTable();

        // Auto-persist new players or XUID updates silently
        if (shouldSave) {
            saveUnifiedManager(true);
        }
    } catch (e) {
        console.error(e);
        if (!silent) alert("載入失敗: " + e.message);
    }
    if (!silent) document.getElementById('loadingOverlay').style.display = 'none';
}

function renderUnifiedTable() {
    const container = document.getElementById('unifiedPlayerTable');
    if (!container) return;

    // Ensure table structure exists
    let table = container.querySelector('table');
    if (!table) {
        container.innerHTML = '';
        const wrapper = document.createElement('div');
        wrapper.className = 'table-responsive';
        table = document.createElement('table');
        table.style.width = '100%';
        table.style.borderCollapse = 'collapse';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>狀態</th>
                    <th>名稱</th>
                    <th>權限</th>
                    <th>白名單</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody></tbody>
        `;
        wrapper.appendChild(table);
        container.appendChild(wrapper);
    }

    const tbody = table.querySelector('tbody');
    const existingRows = Array.from(tbody.querySelectorAll('tr'));
    const rowMap = new Map();

    existingRows.forEach(tr => {
        const name = tr.dataset.name;
        if (name) rowMap.set(name, tr);
    });

    // 1. Update or Add rows
    unifiedPlayers.forEach((p, idx) => {
        let tr = rowMap.get(p.name);

        // Define HTML content for cells
        const statusHtml = p.online ? '<span style="color:#2ecc71">●</span>' : '<span style="color:#7f8c8d">●</span>';
        const nameHtml = p.name;
        // Select logic
        const permValue = p.permission; // visitor, member, operator

        if (!tr) {
            // New Row
            tr = document.createElement('tr');
            tr.dataset.name = p.name;
            tr.style.borderBottom = '1px solid #333';
            tr.innerHTML = `
                <td data-label="狀態" class="status-cell">${statusHtml}</td>
                <td data-label="名稱" style="color:#fff; font-weight:bold;">${nameHtml}</td>
                <td data-label="權限"><select class="perm-select" onchange="updatePlayerProp(${idx}, 'permission', this.value)" style="background:#111; color:#fff; border:1px solid #444; padding:5px; border-radius:4px;">
                    <option value="visitor">訪客 (Visitor)</option>
                    <option value="member">成員 (Member)</option>
                    <option value="operator">管理員 (OP)</option>
                </select></td>
                <td data-label="白名單"><input type="checkbox" class="whitelist-check" onchange="updatePlayerProp(${idx}, 'whitelisted', this.checked)" style="cursor:pointer;"></td>
                <td data-label="操作"><button onclick="removeUnifiedPlayer(${idx})" style="background:#e74c3c; border:none; color:#fff; padding:5px 10px; border-radius:4px;"><i class="fas fa-trash"></i></button></td>
            `;
            tbody.appendChild(tr);

            // Set initial values
            tr.querySelector('.perm-select').value = permValue;
            tr.querySelector('.whitelist-check').checked = p.whitelisted;
        } else {
            // Update Existing Row
            // Update Status (always safe)
            const statusCell = tr.querySelector('.status-cell');
            if (statusCell.innerHTML !== statusHtml) statusCell.innerHTML = statusHtml;

            // Update Background based on online status
            const targetBg = p.online ? 'rgba(46, 204, 113, 0.1)' : 'transparent';
            if (tr.style.background !== targetBg && targetBg !== 'transparent') tr.style.background = targetBg;
            if (!p.online && tr.style.background !== 'transparent') tr.style.background = 'transparent';

            // Update Permission Select (Skip if user is interacting)
            const select = tr.querySelector('.perm-select');
            if (select && document.activeElement !== select) {
                if (select.value !== p.permission) select.value = p.permission;
                // Update onchange index if list order changed (though we Map by name, the index in array matters for delete/update)
                // Actually, passing idx to onclick is dangerous if array sorts/filters. 
                // Better to look up index by name inside updatePlayerProp, OR keep array sync.
                // For now, we update the attr.
                select.setAttribute('onchange', `updatePlayerProp(${idx}, 'permission', this.value)`);
            }

            // Update Whitelist Checkbox
            const check = tr.querySelector('.whitelist-check');
            if (check && document.activeElement !== check) {
                if (check.checked !== p.whitelisted) check.checked = p.whitelisted;
                check.setAttribute('onchange', `updatePlayerProp(${idx}, 'whitelisted', this.checked)`);
            }

            // Update Delete Button Index
            const btn = tr.querySelector('button');
            if (btn) btn.setAttribute('onclick', `removeUnifiedPlayer(${idx})`);
        }

        // Mark as processed
        rowMap.delete(p.name);
    });

    // 2. Remove items that are no longer in the list
    rowMap.forEach((tr) => tr.remove());
}

async function updatePlayerProp(index, key, value) {
    // Record edit time to pause auto-refresh
    lastPlayerEditTime = Date.now();

    const p = unifiedPlayers[index];
    unifiedPlayers[index][key] = value;

    // 如果修改的是權限，立即執行 op/deop 指令以即時生效
    if (key === 'permission') {
        try {
            const nameCallback = `"${p.name}"`;
            let cmd = '';
            if (value === 'operator') {
                cmd = `op ${nameCallback}`;
            } else {
                cmd = `deop ${nameCallback}`;
                // 訪客模式可能需要額外指令，但目前先確保移除 OP
            }

            if (cmd) {
                await fetch(`${BACKEND_URL}/command?key=${API_KEY}&cmd=${encodeURIComponent(cmd)}`);
            }
        } catch (e) {
            console.error("Failed to execute permission command:", e);
        }
    }

    await saveUnifiedManager(true);
}

async function addUnifiedPlayer() {
    const name = prompt("輸入玩家名稱:");
    if (!name) return;
    lastPlayerEditTime = Date.now();
    unifiedPlayers.push({ name: name, xuid: "", permission: "member", whitelisted: true, ignoresLimit: false, online: false });
    renderUnifiedTable(); saveUnifiedManager(true);
}
async function removeUnifiedPlayer(index) {
    if (confirm("確定移除?")) { lastPlayerEditTime = Date.now(); unifiedPlayers.splice(index, 1); renderUnifiedTable(); saveUnifiedManager(true); }
}

async function saveUnifiedManager(silent = false) {
    const allowlist = unifiedPlayers.filter(p => p.whitelisted).map(p => ({ name: p.name, xuid: p.xuid || undefined, ignoresPlayerLimit: p.ignoresLimit }));
    // Bedrock 伺服器的 permissions.json 只接受有 XUID 的玩家
    // 我們同時保存 name 欄位作為參考，以免重啟後無法對應名字
    const permissions = unifiedPlayers
        .filter(p => p.xuid && p.xuid.length > 0)  // 只保存有 XUID 的玩家
        .map(p => ({ permission: p.permission, xuid: p.xuid, name: p.name }));

    const doSave = async () => {
        await fetch(`${BACKEND_URL}/write`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: API_KEY, file: 'allowlist.json', content: JSON.stringify(allowlist, null, 2) }) });
        await fetch(`${BACKEND_URL}/write`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: API_KEY, file: 'permissions.json', content: JSON.stringify(permissions, null, 2) }) });
    };

    if (silent) {
        await handleAutoSave(doSave(), 'saveStatus');
    } else {
        try {
            await doSave();
            alert("儲存成功");
        } catch (e) {
            alert("儲存失敗: " + e.message);
        }
    }
}

// =============================================================================
// [SECTION 3] SERVER PROPERTY MANAGER (server.properties)
// Handles reading/writing the main configuration file with UI generators.
// =============================================================================
const PROPERTY_SCHEMA = {
    // 1. 基本設定
    'server-name': {
        label: '伺服器名稱 (Server Name)',
        type: 'text',
        desc: '伺服器的顯示名稱（顯示在玩家的伺服器列表中）。預設：Dedicated Server'
    },
    'server-port': {
        label: 'IPv4 連接埠 (Port)',
        type: 'number',
        desc: '伺服器的 IPv4 連接埠。除非您有特殊需求或同時開多個服，否則建議保持預設。預設：19132'
    },
    'server-portv6': {
        label: 'IPv6 連接埠 (Port v6)',
        type: 'number',
        desc: '伺服器的 IPv6 連接埠。預設：19133'
    },
    'max-players': {
        label: '最大玩家數 (Max Players)',
        type: 'number',
        desc: '同時在線的最大玩家人數限制。預設：10'
    },
    'online-mode': {
        label: '正版驗證 (Online Mode)',
        type: 'boolean',
        desc: '是否驗證 Xbox Live 登入。true(建議開啟,較安全) / false(關閉,用於LAN測試)。'
    },
    'white-list': {
        label: '白名單 (Whitelist)',
        type: 'boolean',
        desc: '開啟後，只能透過控制台輸入 whitelist add <ID> 添加玩家。true(開啟) / false(關閉)。'
    },

    // 2. 遊戲內容與規則
    'gamemode': {
        label: '遊戲模式 (Gamemode)',
        type: 'select',
        options: ['survival', 'creative', 'adventure'],
        desc: '新玩家進入時的預設遊戲模式。選項：survival(生存)、creative(創造)、adventure(冒險)。'
    },
    'difficulty': {
        label: '難度 (Difficulty)',
        type: 'select',
        options: ['peaceful', 'easy', 'normal', 'hard'],
        desc: '遊戲難度。選項：peaceful(和平)、easy(簡單)、normal(普通)、hard(困難)。'
    },
    'allow-cheats': {
        label: '允許作弊 (Allow Cheats)',
        type: 'boolean',
        desc: '是否允許使用作弊指令 (如 /tp)。即便設為 false，管理員 (OP) 仍可使用指令。'
    },
    'texturepack-required': {
        label: '強制材質包 (Texturepack Required)',
        type: 'boolean',
        desc: '是否強制玩家下載並使用伺服器的資源包。true(強制) / false(不強制)。'
    },

    // 3. 世界設定
    'level-name': {
        label: '世界資料夾 (World Folder)',
        type: 'readonly',
        desc: '這代表「資料夾名稱」。因為修改後會導致伺服器找不到原資料夾而自動創建新世界，為避免誤觸，此欄位已鎖定。如需改名或切換世界，請使用上方的「世界管理」功能。'
    },
    'level-seed': {
        label: '種子碼 (Seed)',
        type: 'text',
        desc: '地圖種子碼。留空則隨機生成。⚠️ 只在世界首次創建時生效，修改現有世界的種子碼無效。'
    },
    'level-type': {
        label: '地圖類型 (Level Type)',
        type: 'select',
        options: ['DEFAULT', 'FLAT', 'LEGACY'],
        desc: '地圖生成類型。'
    },

    // 4. 進階與效能
    'view-distance': {
        label: '視距 (View Distance)',
        type: 'number',
        desc: '玩家能看到的區塊距離。數值越大伺服器負擔越重。建議：預設約 32，卡頓建議調降至 16 或 10。'
    },
    'tick-distance': {
        label: '模擬距離 (Tick Distance)',
        type: 'number',
        desc: '以玩家為中心，生物/作物/紅石運作範圍(4~12)。生存服建議 4 或 6，過高極吃資源。'
    },
    'player-idle-timeout': {
        label: '閒置踢出時間 (Idle Timeout)',
        type: 'number',
        desc: '閒置超過此時間(分鐘)會被踢出。設定 0 代表不踢人。'
    },
    'max-threads': {
        label: '最大執行緒 (Max Threads)',
        type: 'number',
        desc: '伺服器可使用的最大 CPU 執行緒數量。0 代表自動偵測 (建議保持 0)。'
    },

    // 其他預設保留
    'default-player-permission-level': { label: '預設權限', type: 'select', options: ['visitor', 'member', 'operator'], desc: '新玩家預設權限' },
    'content-log-file-enabled': { label: '啟用日誌檔', type: 'boolean', desc: '紀錄錯誤至檔案' },
    'compression-algorithm': { label: '壓縮演算法', type: 'select', options: ['zlib', 'snappy'], desc: '網路傳輸壓縮方式' },
    'server-authoritative-movement': { label: '移動驗證模式', type: 'select', options: ['client-auth', 'server-auth', 'server-auth-with-rewind'], desc: '防止飛行/穿牆外掛 (server-auth)' },
    'correct-player-movement': { label: '修正玩家位置', type: 'boolean', desc: '是否強制回溯異常移動' }
};

let serverPropsContent = "";

function showSection(id) {
    document.querySelectorAll('.section').forEach(el => el.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    if (event && event.currentTarget) event.currentTarget.classList.add('active');

    // Trigger immediate refresh for the new section
    DataManager.refreshAll(false);
}

async function loadInlineServerProperties(silent = false) {
    const form = document.getElementById('inlineOptionsForm');
    if (!form) return;

    if (!silent) form.innerHTML = '<p style="text-align:center; color:#666;">載入中...</p>';

    try {
        const res = await fetch(`${BACKEND_URL}/read?file=server.properties&key=${API_KEY}`);
        const data = await res.json();
        serverPropsContent = data.content;
        renderInlineForm(data.content);
    } catch (e) {
        if (!silent) form.innerHTML = `<p style="color:var(--danger)">載入失敗: ${e.message}</p>`;
        console.error("loadInlineServerProperties error:", e);
    }
}

// -----------------------------------------------------------------------------
// Helper: Localization Map (for readable dropdowns)
// -----------------------------------------------------------------------------
const VALUE_MAP = {
    // Gamemode
    'survival': '生存 (survival)',
    'creative': '創造 (creative)',
    'adventure': '冒險 (adventure)',
    'spectator': '旁觀 (spectator)',
    // Difficulty
    'peaceful': '和平 (peaceful)',
    'easy': '簡單 (easy)',
    'normal': '普通 (normal)',
    'hard': '困難 (hard)',
    // Permissions
    'visitor': '訪客 (visitor)',
    'member': '成員 (member)',
    'operator': '管理員 (operator)',
    // Level Type
    'DEFAULT': '預設 (DEFAULT)',
    'FLAT': '超平坦 (FLAT)',
    'LEGACY': '舊版 (LEGACY)',
    // Movement
    'client-auth': '客戶端驗證 (client-auth)',
    'server-auth': '伺服器驗證 (server-auth)',
    'server-auth-with-rewind': '伺服器驗證並回溯 (server-auth-with-rewind)',
    // Compression
    'zlib': 'zlib (標準)',
    'snappy': 'Snappy (快速)',
    // Bool (fallback if needed, though checkboxes handle this visually)
    'true': '開啟 (true)',
    'false': '關閉 (false)'
};

function renderInlineForm(content) {
    const form = document.getElementById('inlineOptionsForm');
    form.innerHTML = '';

    const lines = content.split('\n');
    const props = {};
    lines.forEach(line => {
        const p = line.split('=');
        if (p.length >= 2) props[p[0].trim()] = p.slice(1).join('=').trim();
    });

    for (const [key, schema] of Object.entries(PROPERTY_SCHEMA)) {
        const val = props[key] || '';
        const wrapper = document.createElement('div');
        wrapper.className = 'form-group';
        wrapper.style.background = '#252830';
        wrapper.style.padding = '15px';
        wrapper.style.borderRadius = '8px';

        const header = document.createElement('div');
        header.style.marginBottom = '8px';
        header.innerHTML = `<label style="display:block; color:#fff; margin-bottom:4px;">${schema.label}</label>
                            <small style="color:#888; font-size:11px;">${schema.desc || key}</small>`;
        wrapper.appendChild(header);

        let input;
        if (schema.type === 'boolean') {
            input = document.createElement('div');
            input.className = val === 'true' ? 'toggle-switch checked' : 'toggle-switch';
            input.dataset.key = key;
            input.dataset.value = val;
            input.innerHTML = '<span></span>';
            input.onclick = function () {
                this.classList.toggle('checked');
                this.dataset.value = this.classList.contains('checked') ? 'true' : 'false';
                saveInlineConfig(true); // Auto-save
            };
        } else if (schema.type === 'select') {
            input = document.createElement('select');
            input.dataset.key = key;
            input.style.width = '100%';
            input.style.padding = '8px';
            input.style.background = '#111';
            input.style.border = '1px solid #444';
            input.style.color = '#fff';
            input.style.borderRadius = '4px';

            schema.options.forEach(opt => {
                const option = document.createElement('option');
                option.value = opt;
                option.innerText = VALUE_MAP[opt] || opt;
                if (val === opt) option.selected = true;
                input.appendChild(option);
            });
            input.onchange = () => saveInlineConfig(true); // Auto-save
        } else if (schema.type === 'readonly') {
            if (key === 'level-name') {
                // [SPECIAL] World Manager Embedded
                input = document.createElement('div');

                // 1. Folder Name (Readonly)
                const folderDiv = document.createElement('div');
                folderDiv.style.marginBottom = '12px';
                folderDiv.innerHTML = '<div style="font-size:11px; color:#888; margin-bottom:4px;">資料夾名稱 (Folder - Locked)</div>';

                const folderInput = document.createElement('input');
                folderInput.type = 'text';
                folderInput.value = val;
                folderInput.disabled = true;
                folderInput.style.width = '100%';
                folderInput.style.padding = '8px';
                folderInput.style.background = '#1a1a1a';
                folderInput.style.border = '1px solid #333';
                folderInput.style.color = '#666';
                folderInput.style.borderRadius = '4px';
                folderInput.style.cursor = 'not-allowed';
                folderDiv.appendChild(folderInput);
                input.appendChild(folderDiv);

                // 2. Display Name (Editable)
                const nameDiv = document.createElement('div');
                nameDiv.innerHTML = '<div style="font-size:11px; color:#ddd; margin-bottom:4px;">顯示名稱 (Display Name - level.dat)</div>';

                const nameWrapper = document.createElement('div');
                nameWrapper.style.display = 'flex';
                nameWrapper.style.gap = '10px';

                const nameInput = document.createElement('input');
                const worldInfo = (window.currentWorlds || []).find(w => w.folder === val);
                nameInput.value = worldInfo ? worldInfo.displayName : val;
                nameInput.type = 'text';
                nameInput.style.flex = '1';
                nameInput.style.padding = '8px';
                nameInput.style.background = '#111';
                nameInput.style.border = '1px solid #444';
                nameInput.style.color = '#fff';
                nameInput.style.borderRadius = '4px';

                const updateBtn = document.createElement('button');
                updateBtn.className = 'btn-aternos btn-blue';
                updateBtn.innerHTML = '<i class="fas fa-save"></i> 改名';
                updateBtn.style.padding = '8px 15px';
                updateBtn.style.whiteSpace = 'nowrap';
                updateBtn.onclick = (e) => {
                    e.preventDefault();
                    if (confirm(`確定要將顯示名稱改為 "${nameInput.value}" 嗎？\n(這不會影響資料夾名稱)`)) {
                        performRenameWorld(val, nameInput.value);
                    }
                };

                nameWrapper.appendChild(nameInput);
                nameWrapper.appendChild(updateBtn);
                nameDiv.appendChild(nameWrapper);
                input.appendChild(nameDiv);

            } else {
                // Standard Read-Only (Legacy fallback)
                input = document.createElement('div');
                input.style.display = 'flex';
                input.style.gap = '10px';
                // ... (simpler version if needed, currently only level-name uses this)
                const display = document.createElement('input');
                display.value = val;
                display.disabled = true; // ...
                // simplified for brevity as currently only level-name is readonly
                display.className = 'form-control disabled'; // Use CSS if available, else style
                display.style.width = '100%';
                display.style.background = '#1a1a1a';
                display.style.border = '1px solid #333';
                display.style.color = '#888';
                display.style.padding = '8px';
                input.appendChild(display);
            }
            // Don't set dataset.key because we don't want to save this field back if it didn't change (though it won't be collected anyway by inputs selector)
        } else {
            input = document.createElement('input');
            input.type = schema.type === 'number' ? 'number' : 'text';
            input.dataset.key = key;
            input.value = val;
            input.style.width = '100%';
            input.style.boxSizing = 'border-box';
            input.style.padding = '8px';
            input.style.background = '#111';
            input.style.border = '1px solid #444';
            input.style.color = '#fff';
            input.style.borderRadius = '4px';
            input.onchange = () => saveInlineConfig(true); // Auto-save
        }

        wrapper.appendChild(input);
        form.appendChild(wrapper);
    }
}

async function saveInlineConfig(silent = false) {
    const form = document.getElementById('inlineOptionsForm');
    const inputs = form.querySelectorAll('[data-key]');
    const newValues = {};

    inputs.forEach(el => {
        newValues[el.dataset.key] = el.dataset.value || el.value;
    });

    // Reconstruct file content preserving comments
    const lines = serverPropsContent.split('\n');
    let finalContent = lines.map(line => {
        const parts = line.split('=');
        if (parts.length >= 2) {
            const key = parts[0].trim();
            if (newValues.hasOwnProperty(key)) {
                return `${key}=${newValues[key]}`;
            }
        }
        return line;
    }).join('\n');

    const doSave = async () => {
        await fetch(`${BACKEND_URL}/write`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key: API_KEY, file: 'server.properties', content: finalContent })
        });
    };

    if (silent) {
        await handleAutoSave(doSave(), 'propSaveStatus');
    } else {
        try {
            await doSave();
            alert("設定儲存成功 (Saved)!");
        } catch (e) {
            alert("儲存失敗: " + e.message);
        }
    }
}

// Helpers
async function handleAutoSave(actionPromise, statusId) {
    const el = document.getElementById(statusId);
    if (!el) return await actionPromise;

    try {
        // 1. Saving State
        el.innerText = "儲存中... (Saving)";
        el.style.color = "#f1c40f"; // Yellow
        el.style.opacity = '1';

        // 2. Execute Action
        const result = await actionPromise;

        // 3. Success State
        el.innerText = "已儲存 (Saved)";
        el.style.color = "var(--success)"; // Green

        // 4. Fade Out
        setTimeout(() => {
            el.style.opacity = '0';
        }, 2000);

        return result;
    } catch (e) {
        // 5. Error State
        console.error("Save failed:", e);
        el.innerText = "失敗 (Failed)";
        el.style.color = "var(--danger)"; // Red
        if (e.message) alert("Save Error: " + e.message);
        throw e;
    }
}

async function getWorldSize() {
    try {
        const res = await fetch(`${BACKEND_URL}/size?key=${API_KEY}`);
        const data = await res.json();

        const sizeEl = document.getElementById('worldSize');
        if (data.size && sizeEl) {
            // Updated to show Name
            let text = data.size;
            if (data.displayName) {
                text += ` <span style="color:#aaa; font-size:11px;">(世界: ${data.displayName})</span>`;
            }
            sizeEl.innerHTML = text;
        }

        // 同時載入世界清單
        await loadWorldList();
    } catch (e) { console.error(e); }
}

// 載入可用世界清單
async function loadWorldList() {
    const container = document.getElementById('worldList');
    if (!container) return;

    try {
        const res = await fetch(`${BACKEND_URL}/worlds?key=${API_KEY}`);
        const data = await res.json();
        window.currentWorlds = data.worlds || []; // Cache for other functions

        if (!data.worlds || data.worlds.length === 0) {
            container.innerHTML = '<span style="color:#666;">沒有找到世界</span>';
            return;
        }

        let html = '';
        data.worlds.forEach(world => {
            const isActive = world.isActive;
            const statusBadge = isActive
                ? '<span style="background:#27ae60; color:white; padding:2px 6px; border-radius:3px; font-size:10px; margin-left:6px;">使用中</span>'
                : '';

            // 操作按鈕區
            // 操作按鈕區
            let actions = '';

            // 編輯按鈕 (所有世界都可以改名)
            const editBtn = `
                <button onclick="renameWorld('${world.folder}', '${world.displayName}')" style="background:#f39c12; border:none; color:white; padding:4px 10px; border-radius:4px; cursor:pointer; font-size:11px; margin-right:4px;">
                    <i class="fas fa-pencil-alt"></i> 改名
                </button>
            `;

            if (!isActive) {
                actions = `
                    ${editBtn}
                    <button onclick="switchWorld('${world.folder}')" style="background:#3498db; border:none; color:white; padding:4px 10px; border-radius:4px; cursor:pointer; font-size:11px; margin-right:4px;">
                        <i class="fas fa-exchange-alt"></i> 切換
                    </button>
                    <button onclick="deleteWorld('${world.folder}')" style="background:#c0392b; border:none; color:white; padding:4px 10px; border-radius:4px; cursor:pointer; font-size:11px;">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                `;
            } else {
                // 使用中的世界只能改名，不能刪除或切換
                actions = editBtn;
            }

            html += `
                <div style="display:flex; justify-content:space-between; align-items:center; padding:8px; background:#1e2127; border-radius:4px; margin-bottom:6px;">
                    <div>
                        <span style="color:#fff; font-size:13px;">${world.displayName}</span>
                        ${statusBadge}
                        <div style="color:#888; font-size:11px; margin-top:2px;">
                            <i class="fas fa-folder"></i> ${world.folder} · <i class="fas fa-hdd"></i> ${world.size}
                        </div>
                    </div>
                    <div style="display:flex; align-items:center;">
                        ${actions}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    } catch (e) {
        console.error('loadWorldList error:', e);
        container.innerHTML = '<span style="color:#e74c3c;">載入失敗</span>';
    }
}

// 重新命名世界
// 重新命名世界 (API Call)
async function performRenameWorld(worldFolder, newName) {
    try {
        const res = await fetch(`${BACKEND_URL}/rename_world?key=${API_KEY}&world=${encodeURIComponent(worldFolder)}&new_name=${encodeURIComponent(newName)}`, {
            method: 'POST'
        });
        const data = await res.json();

        if (res.ok) {
            alert('✅ ' + data.message);
            await loadWorldList(); // Refresh list to update cache
            // If active world, refresh status
            await getWorldSize();
            // Also refresh inline form if open to update Display Name field
            if (document.getElementById('inlineOptionsForm').innerHTML !== '') {
                loadInlineServerProperties(true);
            }
        } else {
            alert('❌ 改名失敗: ' + (data.error || 'Unknown'));
        }
    } catch (e) {
        alert('❌ 請求錯誤: ' + e.message);
    }
}

// 重新命名世界 (UI Prompt)
async function renameWorld(worldFolder, currentDisplayName) {
    const newName = prompt(`請輸入新的世界名稱 (Level Name)\n\n這會修改 level.dat 內部的顯示名稱。\n(⚠️ 這不會改變資料夾名稱)`, currentDisplayName);
    if (!newName || newName === currentDisplayName) return;
    performRenameWorld(worldFolder, newName);
}

// 切換世界
async function switchWorld(worldName) {
    if (!confirm(`確定要切換到世界「${worldName}」嗎？\n\n切換後需要重新啟動伺服器才會生效。\n\n注意：這會切換「世界來源」，遊戲規則 (Gamerules) 將會隨新世界改變。`)) {
        return;
    }

    document.getElementById('loadingOverlay').style.display = 'flex';
    document.getElementById('loadingText').innerText = '正在切換世界...';

    try {
        const res = await fetch(`${BACKEND_URL}/switch_world?key=${API_KEY}&world=${encodeURIComponent(worldName)}`);
        const data = await res.json();

        if (res.ok) {
            // 清除現有的 Gamerules 顯示，避免顯示舊資訊
            const rulesContainer = document.getElementById('gamerulesList');
            if (rulesContainer) rulesContainer.innerHTML = '<div style="padding:20px; text-align:center; color:#888;">等待伺服器啟動以載入新規則...</div>';

            alert('✅ ' + data.message + '\n\n請點擊「停止」再「啟動」來套用變更。');
            await loadWorldList();
        } else {
            alert('❌ 切換失敗: ' + (data.error || 'Unknown'));
        }
    } catch (e) {
        alert('❌ 切換錯誤: ' + e.message);
    } finally {
        document.getElementById('loadingOverlay').style.display = 'none';
    }
}

// 刪除世界
async function deleteWorld(worldName) {
    if (!confirm(`⚠️ 危險操作！⚠️\n\n確定要「永久刪除」世界「${worldName}」嗎？\n此動作無法復原！`)) {
        return;
    }

    // 二次確認
    if (!confirm(`請再次確認：\n\n您真的要刪除「${worldName}」嗎？`)) {
        return;
    }

    document.getElementById('loadingOverlay').style.display = 'flex';
    document.getElementById('loadingText').innerText = '正在刪除世界...';

    try {
        const res = await fetch(`${BACKEND_URL}/delete_world?key=${API_KEY}&world=${encodeURIComponent(worldName)}`, {
            method: 'POST'
        });
        const data = await res.json();

        if (res.ok) {
            alert('✅ ' + data.message);
            await loadWorldList();
        } else {
            alert('❌ 刪除失敗: ' + (data.error || 'Unknown'));
        }
    } catch (e) {
        alert('❌ 刪除錯誤: ' + e.message);
    } finally {
        document.getElementById('loadingOverlay').style.display = 'none';
    }
}

async function execCmd(cmd) {
    try {
        const res = await fetch(`${BACKEND_URL}/exec?key=${API_KEY}&cmd=${encodeURIComponent(cmd)}`);
        return await res.json();
    } catch (e) {
        return { error: e.message };
    }
}

async function runCmd(cmd) { return await fetch(`${BACKEND_URL}/command?key=${API_KEY}&cmd=${encodeURIComponent(cmd)}`); }
function downloadWorld() { window.open(`${BACKEND_URL}/download?key=${API_KEY}`, '_blank'); }
function triggerUpload() { document.getElementById('fileInput').click(); }
function resetWorld() { if (confirm('Reset?')) { execCmd('rm -rf /home/terraria/servers/minecraft/worlds/Bedrock').then(() => alert("Deleted")); } }

async function handleFileUpload(input) {
    const file = input.files[0];
    if (!file) return;

    if (!confirm(`確定要上傳 "${file.name}" 嗎？\n\n如果這是完整備份包 (具有 worlds, behavior_packs 等資料夾)，系統將會進行「全伺服器還原」。\n如果是單一世界檔，將會解壓縮至 worlds 目錄。`)) {
        input.value = '';
        return;
    }

    // [New] Ask for custom folder name
    let folderName = prompt("請為此世界上傳後的資料夾命名 (可選，留空則自動命名):");
    if (folderName === null) {
        input.value = '';
        return; // Cancelled
    }
    folderName = folderName.trim();

    // Show Loading
    document.getElementById('loadingOverlay').style.display = 'flex';
    document.getElementById('loadingText').innerText = '正在上傳並處理世界檔案 (Uploading)...';

    // Build URL
    let uploadUrl = `${BACKEND_URL}/upload?key=${API_KEY}`;
    if (folderName) {
        uploadUrl += `&folder_name=${encodeURIComponent(folderName)}`;
    }

    try {
        const res = await fetch(uploadUrl, {
            method: 'POST',
            body: file
        });
        const data = await res.json();

        if (res.ok) {
            alert('✅ 上傳成功！\n\n' + data.message);
            location.reload();
        } else {
            alert('❌ 上傳失敗: ' + (data.error || 'Unknown Error'));
        }
    } catch (e) {
        alert('❌ 上傳錯誤: ' + e.message);
    } finally {
        document.getElementById('loadingOverlay').style.display = 'none';
        input.value = '';
    }
}


// Load Editor (Legacy/Modal support maintained just in case, but unused for options)
function closeEditor() { document.getElementById('editorModal').style.display = 'none'; }

// --- INIT SHARE LINK ---
window.addEventListener('load', () => {
    const linkSpan = document.getElementById('shareLinkDisplay');
    if (linkSpan) {
        linkSpan.innerText = window.location.origin + '/join.html';
        linkSpan.title = window.location.origin + '/join.html'; // Tooltip for long urls
    }
});



// =============================================================================
// [SECTION 4] ADDON & MOD MANAGER
// Handles uploading, listing, and deleting .mcpack/.mcaddon files.
// =============================================================================

// 載入已安裝的模組清單
async function loadAddons(silent = false) {
    const container = document.getElementById('addonList');
    if (!container) return;

    if (!silent && container.children.length === 0) {
        container.innerHTML = '<div style="text-align:center; padding:20px; color:#aaa;"><i class="fas fa-spinner fa-spin"></i> 載入中...</div>';
    }

    try {
        const res = await fetch(`${BACKEND_URL}/addons?key=${API_KEY}`);
        const data = await res.json();

        if (data.error) {
            if (!silent) container.innerHTML = `<div style="color:#f66; text-align:center; padding:20px;"><i class="fas fa-exclamation-triangle"></i> 載入失敗: ${data.error}</div>`;
            return;
        }

        const addons = data.addons || [];

        if (addons.length === 0) {
            container.innerHTML = `<div style="color:#888; text-align:center; padding:30px;">
                <i class="fas fa-puzzle-piece" style="font-size:24px; margin-bottom:10px; display:block;"></i>
                尚未安裝任何模組
            </div>`;
            return;
        }

        // 渲染模組卡片
        container.innerHTML = addons.map(addon => {
            const version = Array.isArray(addon.version)
                ? addon.version.join('.')
                : addon.version;
            const typeColor = addon.type === '行為包' ? 'var(--btn-blue)' : 'var(--btn-orange)';

            return `
                <div style="display:flex; justify-content:space-between; align-items:center; background:#252830; padding:12px 15px; border-radius:8px; border-left:3px solid ${typeColor};">
                    <div style="flex:1; min-width:0;">
                        <div style="font-weight:bold; color:#fff; margin-bottom:3px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                            ${addon.name}
                        </div>
                        <div style="font-size:11px; color:#888;">
                            <span style="color:${typeColor}; font-weight:bold;">${addon.type}</span>
                            &nbsp;•&nbsp; v${version}
                            ${addon.description ? `<br>${addon.description}` : ''}
                        </div>
                    </div>
                    <button class="btn-aternos" style="background:#c44; min-width:36px; height:36px; padding:0;" 
                        onclick="deleteAddon('${addon.dir}', '${addon.folder}')" title="刪除模組">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
        }).join('');

    } catch (e) {
        container.innerHTML = `<div style="color:#f66; text-align:center; padding:20px;">
            <i class="fas fa-exclamation-triangle"></i> 連接失敗
        </div>`;
        console.error('loadAddons error:', e);
    }
}

// 上傳並安裝模組
async function uploadAddon() {
    const fileInput = document.getElementById('addonFileInput');
    const file = fileInput?.files[0];

    if (!file) {
        alert('請先選擇要安裝的模組檔案 (.mcpack 或 .zip)');
        return;
    }

    try {
        const res = await fetch(`${BACKEND_URL}/addon/upload?key=${API_KEY}`, {
            method: 'POST',
            body: file
        });

        const data = await res.json();

        if (data.error) {
            alert('安裝失敗: ' + data.error);
            return;
        }

        alert(`✓ 模組安裝成功！\n\n名稱: ${data.name}\n類型: ${data.type}\n\n⚠️ 請重啟伺服器以套用模組`);
        fileInput.value = '';  // 清空選擇
        loadAddons();  // 重新載入清單

    } catch (e) {
        alert('上傳失敗: ' + e.message);
        console.error('uploadAddon error:', e);
    }
}

// 刪除模組
async function deleteAddon(dir, folder) {
    if (!confirm(`確定要刪除此模組嗎？\n\n資料夾: ${folder}\n\n此操作無法復原！`)) {
        return;
    }

    try {
        const res = await fetch(`${BACKEND_URL}/addon/delete?key=${API_KEY}&dir=${dir}&folder=${encodeURIComponent(folder)}`, {
            method: 'POST'
        });

        const data = await res.json();

        if (data.error) {
            alert('刪除失敗: ' + data.error);
            return;
        }

        loadAddons();  // 重新載入清單

    } catch (e) {
        alert('刪除失敗: ' + e.message);
        console.error('deleteAddon error:', e);
    }
}

// 頁面載入時也載入模組清單
window.addEventListener('load', () => {
    loadAddons();
});

// =============================================================================
// [SECTION 5] GAME RULE MANAGER (Gamerules)
// Manages in-game rules (keepInventory, mobGriefing, etc.) with real-time syncing.
// =============================================================================
const gameruleConfig = {
    // --- General Rules ---
    'keepinventory': { label: '死亡不掉落', desc: '玩家死亡後保留身上的物品與經驗值', type: 'boolean' },
    'mobgriefing': { label: '生物破壞', desc: '允許怪物 (如苦力怕) 破壞方塊', type: 'boolean' },
    'showcoordinates': { label: '顯示座標', desc: '在畫面上方顯示座標', type: 'boolean' },
    'dodaylightcycle': { label: '日夜循環', desc: '時間自然流動', type: 'boolean' },
    'doweathercycle': { label: '天氣循環', desc: '天氣自動變化', type: 'boolean' },
    'pvp': { label: '玩家傷害', desc: '允許玩家互毆', type: 'boolean' },
    'naturalregeneration': { label: '自然回血', desc: '飽食度高時自動回血', type: 'boolean' },
    'doimmediaterespawn': { label: '立即重生', desc: '免除死亡畫面直接重生', type: 'boolean' },
    'recipesunlock': { label: '配方解鎖', desc: '生存模式需解鎖配方', type: 'boolean' },
    'dolimitedcrafting': { label: '限制合成', desc: '只能合成已解鎖的配方', type: 'boolean' },

    // --- Spawning / Loot ---
    'domobspawning': { label: '生物生成', desc: '生物自然生成', type: 'boolean' },
    'doentitydrops': { label: '實體掉落', desc: '載具/畫框被破壞時掉落', type: 'boolean' },
    'domobloot': { label: '生物掉落', desc: '生物掉落戰利品', type: 'boolean' },
    'dotiledrops': { label: '方塊掉落', desc: '挖掘掉落方塊', type: 'boolean' },
    'doinsomnia': { label: '生成幻翼', desc: '長期未眠生成幻翼', type: 'boolean' },

    // --- Damage / World ---
    'falldamage': { label: '摔落傷害', desc: '高處掉落受傷', type: 'boolean' },
    'firedamage': { label: '火焰傷害', desc: '火/岩漿傷害', type: 'boolean' },
    'drowningdamage': { label: '溺水傷害', desc: '水中溺水傷害', type: 'boolean' },
    'freezedamage': { label: '凍結傷害', desc: '細雪凍傷', type: 'boolean' },
    'dofiretick': { label: '火焰延燒', desc: '火焰蔓延', type: 'boolean' },
    'tntexplodes': { label: 'TNT 爆炸', desc: 'TNT 可爆炸', type: 'boolean' },
    'respawnblocksexplode': { label: '重生錨爆炸', desc: '非地獄使用重生錨爆炸', type: 'boolean' },
    'projectilescanbreakblocks': { label: '投射物破壞', desc: '三叉戟等破壞方塊', type: 'boolean' },
    'tntexplosiondropdecay': { label: 'TNT 掉落衰減', desc: 'TNT 爆炸掉落物衰減', type: 'boolean' },

    // --- Chat / UI ---
    'showdeathmessages': { label: '顯示死亡訊息', desc: '聊天欄顯示死因', type: 'boolean' },
    'showtags': { label: '顯示標籤', desc: '物品顯示 NBT 標籤', type: 'boolean' },
    'showbordereffect': { label: '顯示邊界效果', desc: '邊界紅色粒子', type: 'boolean' },
    'locatorbar': { label: '定位器條', desc: 'Locator Bar 顯示 (部分客戶端)', type: 'boolean' },
    'showdaysplayed': { label: '顯示遊玩天數', desc: '顯示世界遊玩天數', type: 'boolean' },
    'showrecipemessages': { label: '顯示配方訊息', desc: '解鎖配方時顯示提示', type: 'boolean' },
    'sendcommandfeedback': { label: '指令回饋', desc: '顯示指令執行結果', type: 'boolean' },
    'commandblocksenabled': { label: '啟用指令方塊', desc: '允許指令方塊運作', type: 'boolean' },
    'commandblockoutput': { label: '指令方塊輸出', desc: '顯示指令方塊日誌', type: 'boolean' },

    // --- Numeric Rules (Integers) ---
    'randomtickspeed': { label: '隨機刻速度', desc: '作物生長速度 (預設 1，過高會卡)', type: 'number' },
    'spawnradius': { label: '重生半徑', desc: '無床重生範圍 (格)', type: 'number' },
    'playerssleepingpercentage': { label: '入睡百分比', desc: '跳過夜晚比例 (0-100)', type: 'number' },
    'maxcommandchainlength': { label: '指令鏈上限', desc: '連鎖指令最大數量', type: 'number' },
    'functioncommandlimit': { label: 'Function 上限', desc: '單函數指令上限', type: 'number' }
};

async function loadGameRules(silent = false) {
    const list = document.getElementById('gameruleList');
    if (!list) return;

    // Only show loading text if list is empty (first load) and not silent
    if (!silent && list.children.length === 0) {
        list.innerHTML = '<p style="text-align:center; color:#666; width:100%;">正在讀取規則 (Reading Rules)...</p>';
    }

    // Optimization: Don't spam commands if we just fetched recently (debounce 3s)
    // accessible from global scope or strictly inside? We need global tracking.
    // Assuming lastRuleFetchTime is defined globally. If not, define it here (scoping issue).
    // Let's rely on checking if we are already "good". 
    // Actually, create a static var by checking window.
    // 快取機制：5分鐘內不重新查詢
    if (!window.lastRuleFetchTime) window.lastRuleFetchTime = 0;
    if (!window.cachedRuleValues) window.cachedRuleValues = null;

    const now = Date.now();
    const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes
    let skipCommands = (now - window.lastRuleFetchTime < CACHE_DURATION && window.cachedRuleValues);

    try {
        if (!skipCommands) {
            window.lastRuleFetchTime = now;
            // 1. Send query commands (Parallel)
            // Reduce command spam: Only query active rules if possible? No, we need all.
            const promises = Object.keys(gameruleConfig).map(rule =>
                fetch(`${BACKEND_URL}/command?key=${API_KEY}&cmd=${encodeURIComponent('gamerule ' + rule)}`)
            );
            await Promise.all(promises);
            // 2. Wait for log write (optimized: 300ms is sufficient)
            await new Promise(r => setTimeout(r, 300));
        }

        // 3. Read log (Optimized: Read only last 1000 lines)
        const logRes = await fetch(`${BACKEND_URL}/read?key=${API_KEY}&file=bedrock_screen.log&lines=1000`);
        const logText = logRes.ok ? (await logRes.json()).content || "" : "";

        // 4. Parse log (find last occurrence of "gamerule = value")
        const values = {};
        const lines = logText.split('\n');
        lines.forEach(line => {
            // Updated Regex to support integers
            const match = line.match(/\b([a-zA-Z_]+)\s*=\s*(true|false|\d+)\b/i);
            if (match) {
                const key = match[1].toLowerCase();
                const rawVal = match[2].toLowerCase();
                if (gameruleConfig[key]) {
                    if (gameruleConfig[key].type === 'number') {
                        values[key] = parseInt(rawVal);
                    } else {
                        values[key] = (rawVal === 'true');
                    }
                }
            }
        });

        // Save to cache
        if (!skipCommands) {
            window.cachedRuleValues = values;
        }

        // Use cached values if we skipped commands
        const finalValues = skipCommands ? window.cachedRuleValues : values;

        // 5. Render or Update
        if (list.children.length === 0 || list.querySelector('p')) {
            list.innerHTML = '';
            for (let rule in gameruleConfig) {
                const conf = gameruleConfig[rule];
                const val = finalValues[rule] !== undefined ? finalValues[rule] : (conf.type === 'number' ? 0 : false);

                let inputHtml = '';
                if (rule === 'playerssleepingpercentage') {
                    // [NEW] Dual input (Range + Number) with strict alignment
                    inputHtml = `
                        <div style="display:flex; align-items:center; gap:8px; background:#222; padding:4px 8px; border-radius:4px; border:1px solid #444; flex-shrink:0;">
                            <input type="range" id="input_${rule}_range" min="0" max="100" value="${val}" 
                                   style="width:100px; height:20px; margin:0; padding:0; vertical-align:middle; cursor:pointer; background:transparent;" 
                                   oninput="document.getElementById('input_${rule}').value = this.value"
                                   onchange="updateGameRule('${rule}', this.value)">
                            
                            <div style="display:flex; align-items:center; justify-content:center; height:20px;">
                                <input type="number" id="input_${rule}" min="0" max="100" value="${val}" 
                                       style="width:36px; height:20px; line-height:20px; text-align:center; background:transparent; border:none; color:#fff; font-weight:bold; padding:0; margin:0; -moz-appearance:textfield;"
                                       oninput="document.getElementById('input_${rule}_range').value = this.value"
                                       onchange="updateGameRule('${rule}', this.value)">
                                <span style="color:#888; font-size:12px; line-height:20px; margin-left:2px; padding-top:2px;">%</span>
                            </div>
                        </div>
                    `;
                } else if (conf.type === 'number') {
                    inputHtml = `<input type="number" id="input_${rule}" value="${val}" style="width:80px; text-align:center; padding:5px; background:#222; border:1px solid #555; color:white; border-radius:4px;" onchange="updateGameRule('${rule}', this.value)">`;
                } else {
                    inputHtml = `
                        <label class="switch">
                            <input type="checkbox" id="input_${rule}" onchange="updateGameRule('${rule}', this.checked)" ${val ? 'checked' : ''}>
                            <span class="slider round"></span>
                        </label>`;
                }

                const wrapper = document.createElement('div');
                wrapper.style.marginBottom = '10px';
                wrapper.innerHTML = `
                    <div style="background:#111; padding:10px; border-radius:4px; border:1px solid #444;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="color:#eee; font-size:14px; font-weight:bold;">${conf.label}</span>
                            ${inputHtml}
                        </div>
                        <div style="color:#888; font-size:12px; margin-top:5px; line-height:1.4;">${conf.desc || ''}</div>
                    </div>
                `;
                list.appendChild(wrapper);
            }
        } else {
            // Update existing elements
            for (let rule in gameruleConfig) {
                const val = finalValues[rule];
                if (val === undefined) continue;

                const input = document.getElementById(`input_${rule}`);
                if (!input) continue;
                if (document.activeElement === input) continue;

                if (input.type === 'checkbox') {
                    if (input.checked !== val) input.checked = val;
                } else {
                    if (parseFloat(input.value) !== val) {
                        input.value = val;
                        // Also update range if exists (for sleeping percentage)
                        const range = document.getElementById(`input_${rule}_range`);
                        if (range && document.activeElement !== range) {
                            range.value = val;
                        }
                    }
                }
            }
        }
    } catch (e) {
        console.error("Auto-refresh failed", e);
    }
}

async function updateGameRule(rule, value) {
    const cmd = `gamerule ${rule} ${value}`;
    // Rule updates are always "silent" in terms of not blocking with alert, 
    // but we want visual feedback.
    await handleAutoSave(
        fetch(`${BACKEND_URL}/command?key=${API_KEY}&cmd=${encodeURIComponent(cmd)}`),
        'ruleSaveStatus'
    );
}



// Start Global Syncs (Safe Init)
startPlayerAutoRefresh();
startRuleSync();
// =============================================================================
// [SECTION 5] SERVER UPDATE
// =============================================================================
async function updateServer() {
    const input = document.getElementById('updateUrlInput');
    const url = input.value.trim();

    if (!url) {
        alert('請輸入下載連結！ (Please enter download URL)');
        return;
    }

    if (!confirm('⚠️ 警告 (Warning)\n\n系統將會：\n1. 停止伺服器\n2. 備份設定檔\n3. 覆蓋核心檔案\n4. 還原設定檔\n\n請問確定要繼續嗎？')) {
        return;
    }

    // Show Loading
    const btn = document.querySelector('button[onclick="updateServer()"]');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 更新中... (Updating)';

    try {
        const res = await fetch(`${BACKEND_URL}/update?key=${API_KEY}&url=${encodeURIComponent(url)}`);
        const data = await res.json();

        if (res.ok) {
            alert('✅ 更新完成！ (Update Success)\n\n' + data.status);
            input.value = '';
            // Refresh Status (Server is stopped now)
            setTimeout(updateServerStatus, 1000);
        } else {
            alert('❌ 更新失敗 (Failed): ' + data.error);
        }
    } catch (e) {
        alert('❌ 請求錯誤: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// =============================================================================
// [SECTION 6] WEB CONFIG MANAGER
// =============================================================================
async function loadWebConfig() {
    try {
        const res = await fetch('/public_config?t=' + Date.now());
        if (res.ok) {
            const conf = await res.json();
            const input = document.getElementById('serverTitleInput');
            if (input && conf.server_title) {
                input.value = conf.server_title;
            }
        }
    } catch (e) {
        console.error("Failed to load web config", e);
    }
}

async function saveWebConfig() {
    const title = document.getElementById('serverTitleInput').value.trim();
    const btn = document.querySelector('button[onclick="saveWebConfig()"]');

    // UI Feedback
    const oldHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 儲存中...';
    btn.disabled = true;

    try {
        const res = await fetch(`${BACKEND_URL}/save_config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                key: API_KEY,
                config: {
                    server_title: title
                }
            })
        });

        if (res.ok) {
            alert("✅ 網頁設定已儲存！\n\n邀請頁面的標題已更新。");
        } else {
            const err = await res.json();
            alert("❌ 儲存失敗: " + (err.error || "Unknown"));
        }
    } catch (e) {
        alert("❌ 請求錯誤: " + e.message);
    } finally {
        btn.innerHTML = oldHtml;
        btn.disabled = false;
    }
}


// Load on init - Handled by DataManager now
