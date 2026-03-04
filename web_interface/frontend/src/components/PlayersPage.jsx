// PlayersPage.jsx — 白名單與權限管理頁面 (舊版配色)
import { useState, useEffect } from 'react';
import { readFile, writeFile } from '../utils/api';

export default function PlayersPage() {
    const [allowlist, setAllowlist] = useState([]);
    const [permissions, setPermissions] = useState([]);
    const [newPlayer, setNewPlayer] = useState('');
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');

    // 載入白名單與權限
    useEffect(() => {
        const load = async () => {
            try {
                const alRes = await readFile('allowlist.json');
                if (alRes?.content) setAllowlist(JSON.parse(alRes.content));
            } catch (_) { }
            try {
                const pmRes = await readFile('permissions.json');
                if (pmRes?.content) setPermissions(JSON.parse(pmRes.content));
            } catch (_) { }
        };
        load();
    }, []);

    // 新增玩家
    const handleAdd = () => {
        if (!newPlayer.trim()) return;
        const exists = allowlist.some(p => p.name?.toLowerCase() === newPlayer.toLowerCase());
        if (exists) { setMessage('⚠️ 該玩家已在清單中'); return; }
        setAllowlist(prev => [...prev, { ignoresPlayerLimit: false, name: newPlayer.trim() }]);
        setNewPlayer('');
        setMessage('');
    };

    // 移除玩家
    const handleRemove = (name) => {
        setAllowlist(prev => prev.filter(p => p.name !== name));
    };

    // 修改權限等級
    const handlePermissionChange = (xuid, newLevel) => {
        setPermissions(prev => prev.map(p =>
            p.xuid === xuid ? { ...p, permission: newLevel } : p
        ));
    };

    // 儲存
    const handleSave = async () => {
        setSaving(true);
        setMessage('');
        try {
            await writeFile('allowlist.json', JSON.stringify(allowlist, null, 2));
            await writeFile('permissions.json', JSON.stringify(permissions, null, 2));
            setMessage('✅ 已儲存！重啟伺服器後生效。');
        } catch (e) {
            setMessage('❌ 儲存失敗: ' + e.message);
        }
        setSaving(false);
    };

    return (
        <div className="flex flex-col gap-4">
            {/* 標題 */}
            <div className="flex justify-between items-center">
                <h2 className="text-xl font-bold">玩家管理 (Player Manager)</h2>
                <span className={`text-xs text-success font-bold transition-opacity ${message ? 'opacity-100' : 'opacity-0'}`}>
                    {message}
                </span>
            </div>

            {/* 白名單 */}
            <div className="glass-panel p-6 rounded-2xl">
                <h3 className="font-semibold flex items-center gap-2 mb-4">
                    <i className="fas fa-shield-alt text-success"></i>
                    白名單 (Allowlist)
                    <span className="text-xs text-text-sub ml-auto">{allowlist.length} 位玩家</span>
                </h3>

                {/* 新增區 */}
                <div className="flex gap-2 mb-4">
                    <input
                        type="text"
                        value={newPlayer}
                        onChange={(e) => setNewPlayer(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
                        placeholder="輸入玩家名稱..."
                        className="flex-1 bg-black/30 border border-white/10 rounded-lg px-4 py-2 text-white text-sm placeholder:text-slate-600 outline-none focus:border-success/50"
                    />
                    <button onClick={handleAdd} className="btn-action bg-success/20 text-success hover:bg-success/30">
                        <i className="fas fa-plus"></i> 新增
                    </button>
                </div>

                {/* 玩家清單 */}
                <div className="space-y-2 max-h-60 overflow-y-auto custom-scrollbar">
                    {allowlist.map((player, i) => (
                        <div key={i} className="flex items-center justify-between bg-black/20 rounded-xl px-4 py-3 group hover:bg-black/30 transition-all">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full bg-success/20 flex items-center justify-center text-xs font-bold text-success">
                                    {(player.name || '?')[0].toUpperCase()}
                                </div>
                                <span className="text-white text-sm">{player.name}</span>
                            </div>
                            <button onClick={() => handleRemove(player.name)}
                                className="text-red-400/50 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100">
                                <i className="fas fa-times"></i>
                            </button>
                        </div>
                    ))}
                    {allowlist.length === 0 && (
                        <p className="text-text-sub text-sm text-center py-4">尚無白名單玩家</p>
                    )}
                </div>
            </div>

            {/* 權限區 */}
            <div className="glass-panel p-6 rounded-2xl">
                <h3 className="font-semibold flex items-center gap-2 mb-4">
                    <i className="fas fa-user-shield text-btn-blue"></i>
                    權限管理 (Permissions)
                </h3>
                <div className="space-y-2 max-h-60 overflow-y-auto custom-scrollbar">
                    {permissions.map((p, i) => (
                        <div key={i} className="flex items-center justify-between bg-black/20 rounded-xl px-4 py-3">
                            <span className="text-white text-sm">{p.xuid || 'Unknown'}</span>
                            <select
                                value={p.permission || 'member'}
                                onChange={(e) => handlePermissionChange(p.xuid, e.target.value)}
                                className="bg-black/30 border border-white/10 rounded-lg px-3 py-1 text-white text-sm outline-none"
                            >
                                <option value="visitor">Visitor</option>
                                <option value="member">Member</option>
                                <option value="operator">Operator</option>
                            </select>
                        </div>
                    ))}
                    {permissions.length === 0 && (
                        <p className="text-text-sub text-sm text-center py-4">尚無自訂權限</p>
                    )}
                </div>
            </div>

            {/* 儲存按鈕 */}
            <div className="flex items-center gap-4">
                <button onClick={handleSave} disabled={saving}
                    className="btn-power"
                >
                    {saving ? '儲存中...' : '💾 儲存變更'}
                </button>
                {message && <span className="text-sm">{message}</span>}
            </div>
        </div>
    );
}
