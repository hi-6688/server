// ConsolePage.jsx — 即時終端機頁面 (獨立全畫面版本，舊版配色)
import { useState, useEffect, useRef } from 'react';
import { readFile, sendCommand } from '../utils/api';

export default function ConsolePage() {
    const [logs, setLogs] = useState([]);
    const [commandInput, setCommandInput] = useState('');
    const logsEndRef = useRef(null);

    // 每 3 秒自動拉取最新日誌
    useEffect(() => {
        const pullLogs = async () => {
            try {
                const data = await readFile('bedrock_screen.log', 50);
                if (data && data.content) {
                    const lines = data.content.split('\n').filter(l => l.trim()).map((line, i) => ({
                        id: i,
                        time: '',
                        level: 'INFO',
                        message: line
                    }));
                    setLogs(lines);
                }
            } catch (_) { /* 靜默 */ }
        };

        pullLogs();
        const interval = setInterval(pullLogs, 3000);
        return () => clearInterval(interval);
    }, []);

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
        setLogs(prev => [...prev, { id: Date.now(), time: timeStr, level: 'CMD', message: '> ' + cmd }]);

        try {
            await sendCommand(cmd);
        } catch (e) {
            setLogs(prev => [...prev, { id: Date.now(), time: timeStr, level: 'ERROR', message: 'Failed: ' + e.message }]);
        }
    };

    return (
        <div className="flex-1 glass-panel rounded-2xl p-0 flex flex-col overflow-hidden">
            {/* 標題列 */}
            <div className="h-14 border-b border-white/10 flex items-center px-6 shrink-0">
                <i className="fas fa-terminal text-success mr-3"></i>
                <h2 className="text-white font-semibold">伺服器終端機</h2>
                <span className="ml-auto text-xs text-text-sub">每 3 秒自動刷新</span>
            </div>

            {/* 日誌區 */}
            <div className="flex-1 overflow-y-auto p-4 font-mono text-sm space-y-1 custom-scrollbar bg-black/20">
                {logs.map((log) => (
                    <div key={log.id} className="flex gap-2">
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
