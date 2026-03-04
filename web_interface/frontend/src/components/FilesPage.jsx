// FilesPage.jsx — 世界地圖與模組管理頁面 (舊版配色)
import { useState, useEffect } from 'react';
import { fetchWorlds, fetchAddons, switchWorld, deleteWorld, deleteAddon } from '../utils/api';

export default function FilesPage() {
    const [worlds, setWorlds] = useState([]);
    const [activeWorld, setActiveWorld] = useState('');
    const [addons, setAddons] = useState([]);
    const [message, setMessage] = useState('');

    // 載入世界與模組
    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const wRes = await fetchWorlds();
            if (wRes) {
                setWorlds(wRes.worlds || []);
                setActiveWorld(wRes.active || '');
            }
        } catch (_) { }
        try {
            const aRes = await fetchAddons();
            if (aRes) setAddons(aRes.addons || []);
        } catch (_) { }
    };

    // 切換世界
    const handleSwitch = async (worldName) => {
        try {
            await switchWorld(worldName);
            setActiveWorld(worldName);
            setMessage('✅ 已切換至 ' + worldName + '，重啟伺服器後生效');
        } catch (e) {
            setMessage('❌ 切換失敗: ' + e.message);
        }
    };

    // 刪除世界
    const handleDeleteWorld = async (worldName) => {
        if (!confirm('確定要刪除世界 "' + worldName + '"？此操作不可復原！')) return;
        try {
            await deleteWorld(worldName);
            setWorlds(prev => prev.filter(w => w !== worldName));
            setMessage('🗑️ 已刪除 ' + worldName);
        } catch (e) {
            setMessage('❌ 刪除失敗: ' + e.message);
        }
    };

    // 刪除模組
    const handleDeleteAddon = async (addonName, addonType) => {
        if (!confirm('確定要刪除模組 "' + addonName + '"？')) return;
        try {
            await deleteAddon(addonName, addonType);
            setAddons(prev => prev.filter(a => a.name !== addonName));
            setMessage('🗑️ 已刪除 ' + addonName);
        } catch (e) {
            setMessage('❌ 刪除失敗: ' + e.message);
        }
    };

    return (
        <div className="flex flex-col gap-4">
            {/* 標題 */}
            <h2 className="text-xl font-bold">世界管理</h2>

            {/* 訊息提示 */}
            {message && (
                <div className="glass-panel rounded-2xl px-4 py-3 text-sm">{message}</div>
            )}

            {/* 世界管理 */}
            <div className="glass-panel p-6 rounded-2xl">
                <h3 className="font-semibold flex items-center gap-2 mb-4">
                    <i className="fas fa-globe-americas text-success"></i>
                    可用世界 (Worlds)
                </h3>

                <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
                    {worlds.map((world, i) => (
                        <div key={i} className="flex items-center justify-between bg-black/20 rounded-xl px-4 py-3 group hover:bg-black/30 transition-all">
                            <div className="flex items-center gap-3">
                                <i className="fas fa-map text-text-sub"></i>
                                <span className="text-white text-sm">{world}</span>
                                {world === activeWorld && (
                                    <span className="text-xs bg-success/20 text-success px-2 py-0.5 rounded-full">使用中</span>
                                )}
                            </div>
                            <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                {world !== activeWorld && (
                                    <button onClick={() => handleSwitch(world)}
                                        className="text-xs bg-btn-blue/20 text-btn-blue px-3 py-1 rounded-lg hover:bg-btn-blue/30 transition-all">
                                        切換
                                    </button>
                                )}
                                <button onClick={() => handleDeleteWorld(world)}
                                    className="text-xs bg-red-500/20 text-red-400 px-3 py-1 rounded-lg hover:bg-red-500/30 transition-all">
                                    刪除
                                </button>
                            </div>
                        </div>
                    ))}
                    {worlds.length === 0 && (
                        <p className="text-text-sub text-sm text-center py-4">無法載入世界清單</p>
                    )}
                </div>
            </div>

            {/* 模組管理 */}
            <div className="glass-panel p-6 rounded-2xl">
                <h3 className="font-semibold flex items-center gap-2 mb-4">
                    <i className="fas fa-puzzle-piece text-btn-orange"></i>
                    模組管理 (Addons)
                </h3>

                <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
                    {addons.map((addon, i) => (
                        <div key={i} className="flex items-center justify-between bg-black/20 rounded-xl px-4 py-3 group hover:bg-black/30 transition-all">
                            <div className="flex items-center gap-3">
                                <i className={`fas ${addon.type === 'resource_packs' ? 'fa-palette text-btn-blue' : 'fa-code text-btn-orange'}`}></i>
                                <div>
                                    <span className="text-white text-sm block">{addon.name}</span>
                                    <span className="text-text-sub text-xs">{addon.type === 'resource_packs' ? '材質包' : '行為包'}</span>
                                </div>
                            </div>
                            <button onClick={() => handleDeleteAddon(addon.name, addon.type)}
                                className="text-red-400/50 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100">
                                <i className="fas fa-trash"></i>
                            </button>
                        </div>
                    ))}
                    {addons.length === 0 && (
                        <p className="text-text-sub text-sm text-center py-4">尚無已安裝模組</p>
                    )}
                </div>
            </div>
        </div>
    );
}
