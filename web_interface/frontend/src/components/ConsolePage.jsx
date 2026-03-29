// ConsolePage.jsx — 即時終端機頁面 (獨立全畫面版本，舊版配色，WebSocket 版)
import { useState, useEffect, useRef } from 'react';
import { sendCommand as sendCommandToConsole } from '../utils/api';

export default function ConsolePage({ logs, setLogs, isConnected, sendCommand }) {
    const [commandInput, setCommandInput] = useState('');
    const logsEndRef = useRef(null);

    // 自動捲動到底部
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    // 發送指令
    const handleSend = async () => {
        if (!commandInput.trim()) return;
        const cmd = commandInput;
        setCommandInput('');

        const now = new Date();
        const pad = (n) => String(n).padStart(2, '0');
        const timeStr = pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());

        // 優先使用 WebSocket 發送，若不通則 fallback HTTP
        if (isConnected && sendCommand) {
             sendCommand(cmd);
             // 樂觀更新 UI
             setLogs(prev => [...prev, { id: Date.now(), time: timeStr, level: 'CMD', message: '> ' + cmd }]);
        } else {
             setLogs(prev => [...prev, { id: Date.now(), time: timeStr, level: 'CMD', message: '> ' + cmd }]);
             try {
                 await sendCommandToConsole(cmd);
             } catch (e) {
                 setLogs(prev => [...prev, { id: Date.now(), time: timeStr, level: 'ERROR', message: 'Failed: ' + e.message }]);
             }
        }
    };

    return (
        <div className="flex-1 glass-panel rounded-2xl p-0 flex flex-col overflow-hidden">
            {/* 標題列 */}
            <div className="h-14 border-b border-white/10 flex items-center px-6 shrink-0">
                <i className="fas fa-terminal text-success mr-3"></i>
                <h2 className="text-white font-semibold">伺服器終端機</h2>
                <div className="ml-auto flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success shadow-[0_0_8px_#4ade80]' : 'bg-red-500 shadow-[0_0_8px_#ef4444]'}`}></div>
                    <span className="text-xs text-text-sub">{isConnected ? '即時連線中' : '連線中斷'}</span>
                </div>
            </div>

            {/* 日誌區 */}
            <div className="flex-1 overflow-y-auto p-4 font-mono text-sm space-y-1 custom-scrollbar bg-black/20">
                {logs.map((log, index) => (
                    <div key={log.id || index} className="flex gap-2 hover:bg-white/5 px-1 rounded transition-colors">
                        {log.time && <span className="text-slate-600 shrink-0">[{log.time}]</span>}
                        <span className={
                            log.level === 'CMD' ? 'text-cyan-400' :
                                log.level === 'ERROR' ? 'text-red-400' :
                                    'text-slate-300'
                        }>{log.message}</span>
                    </div>
                ))}
                <div ref={logsEndRef} />
            </div>

            {/* 指令輸入 */}
            <div className="h-14 border-t border-white/10 flex items-center px-4 gap-3 shrink-0">
                <span className="text-success font-mono">$</span>
                <input
                    type="text"
                    value={commandInput}
                    onChange={(e) => setCommandInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    placeholder="輸入伺服器指令..."
                    className="flex-1 bg-transparent text-white placeholder:text-slate-600 outline-none font-mono text-sm"
                />
                <button
                    onClick={handleSend}
                    className="px-4 py-2 rounded-xl bg-success/20 text-success hover:bg-success/30 transition-all text-sm font-medium"
                >
                    送出
                </button>
            </div>
        </div>
    );
}
