// SettingsPage.jsx — server.properties 設定編輯器 (舊版配色)
import { useState, useEffect } from 'react';
import { readFile, writeFile, fetchVersion } from '../utils/api';

export default function SettingsPage() {
    const [properties, setProperties] = useState([]);
    const [version, setVersion] = useState('Unknown');
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');

    // 載入 server.properties 與版本
    useEffect(() => {
        const load = async () => {
            try {
                const res = await readFile('server.properties');
                if (res?.content) {
                    const lines = res.content.split('\n')
                        .filter(l => l.trim() && !l.startsWith('#'))
                        .map(l => {
                            const [key, ...rest] = l.split('=');
                            return { key: key.trim(), value: rest.join('=').trim() };
                        })
                        .filter(p => p.key);
                    setProperties(lines);
                }
            } catch (_) { }
            try {
                const vRes = await fetchVersion();
                if (vRes?.version) setVersion(vRes.version);
            } catch (_) { }
        };
        load();
    }, []);

    // 修改設定值
    const handleChange = (key, newValue) => {
        setProperties(prev => prev.map(p =>
            p.key === key ? { ...p, value: newValue } : p
        ));
    };

    // 儲存
    const handleSave = async () => {
        setSaving(true);
        setMessage('');
        try {
            const content = properties.map(p => p.key + '=' + p.value).join('\n') + '\n';
            await writeFile('server.properties', content);
            setMessage('✅ 設定已儲存！重啟伺服器後生效。');
        } catch (e) {
            setMessage('❌ 儲存失敗: ' + e.message);
        }
        setSaving(false);
    };

    // 判斷值的類型以選擇適當的輸入方式
    const renderInput = (prop) => {
        if (prop.value === 'true' || prop.value === 'false') {
            return (
                <button
                    onClick={() => handleChange(prop.key, prop.value === 'true' ? 'false' : 'true')}
                    className={`px-3 py-1 rounded-lg text-sm font-medium transition-all ${prop.value === 'true'
                        ? 'bg-success/20 text-success hover:bg-success/30'
                        : 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                        }`}
                >
                    {prop.value}
                </button>
            );
        }
        return (
            <input
                type="text"
                value={prop.value}
                onChange={(e) => handleChange(prop.key, e.target.value)}
                className="bg-black/30 border border-white/10 rounded-lg px-3 py-1 text-white text-sm outline-none focus:border-btn-blue/50 w-48 text-right"
            />
        );
    };

    return (
        <div className="flex flex-col gap-4">
            {/* 標題 */}
            <div className="flex justify-between items-center sticky top-0 z-10 py-2">
                <h2 className="text-xl font-bold">伺服器設定 (Server Properties)</h2>
                <span className={`text-xs text-success font-bold transition-opacity ${message ? 'opacity-100' : 'opacity-0'}`}>
                    {message}
                </span>
            </div>

            {/* 提醒 */}
            <div className="flex items-center gap-3 bg-yellow-500/15 border border-yellow-500 rounded-lg px-4 py-3">
                <i className="fas fa-exclamation-triangle text-yellow-500 text-lg"></i>
                <span className="text-yellow-500 text-sm">修改的設定將在<strong>下次重啟伺服器後</strong>生效。</span>
            </div>

            {/* 伺服器資訊 */}
            <div className="glass-panel p-6 rounded-2xl">
                <h3 className="font-semibold flex items-center gap-2 mb-4">
                    <i className="fas fa-info-circle text-btn-blue"></i>
                    伺服器資訊
                </h3>
                <div className="flex gap-6 text-sm">
                    <div>
                        <span className="text-text-sub block">伺服器版本</span>
                        <span className="text-white font-mono">{version}</span>
                    </div>
                    <div>
                        <span className="text-text-sub block">設定檔</span>
                        <span className="text-white font-mono">server.properties</span>
                    </div>
                    <div>
                        <span className="text-text-sub block">屬性數量</span>
                        <span className="text-white font-mono">{properties.length}</span>
                    </div>
                </div>
            </div>

            {/* 設定清單 */}
            <div className="glass-panel p-6 rounded-2xl">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold flex items-center gap-2">
                        <i className="fas fa-cogs text-btn-orange"></i>
                        伺服器設定
                    </h3>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="btn-power text-sm px-4 py-2"
                    >
                        {saving ? '儲存中...' : '💾 儲存'}
                    </button>
                </div>

                {message && <div className="text-sm mb-3">{message}</div>}

                <div className="space-y-1 max-h-96 overflow-y-auto custom-scrollbar">
                    {properties.map((prop, i) => (
                        <div key={i} className="flex items-center justify-between bg-black/20 rounded-xl px-4 py-2.5 hover:bg-black/30 transition-all">
                            <span className="text-slate-300 text-sm font-mono">{prop.key}</span>
                            {renderInput(prop)}
                        </div>
                    ))}
                    {properties.length === 0 && (
                        <p className="text-text-sub text-sm text-center py-4">無法載入設定檔</p>
                    )}
                </div>
            </div>
        </div>
    );
}
