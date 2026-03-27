// ConsolePage.jsx — 即時終端機頁面 (獨立全畫面版本，舊版配色)
import { useState, useEffect, useRef } from 'react';
import { readFile } from '../utils/api';

export default function ConsolePage({ logs, sendCommand, isConnected }) {
    const [historyLogs, setHistoryLogs] = useState([]);
    const [commandInput, setCommandInput] = useState('');
    const logsEndRef = useRef(null);

    // 首次載入時拉取最後 50 行歷史日誌
    useEffect(() => {
        const pullHistory = async () => {
            try {
                const data = await readFile('bedrock_screen.log', 50);
                if (data && data.content) {
                    const lines = data.content.split('\n').filter(l => l.trim()).map((line, i) => ({
                        id: `hist-${i}`,
                        time: '',
                        level: 'INFO',
                        message: line
                    }));
                    setHistoryLogs(lines);
                }
            } catch (_) { /* 靜默 */ }
        };
        pullHistory();
    }, []);

    // 合併歷史日誌與最新的 WebSocket 日誌
    const displayLogs = [...historyLogs, ...logs.map((L, i) => ({ ...L, id: `ws-${i}` }))];

    // 自動捲動到底部
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [displayLogs]);

    // 發送指令
    const handleSend = async () => {
        if (!commandInput.trim()) return;
        const cmd = commandInput;
        setCommandInput('');
        
        // 呼叫 App 傳遞進來的 sendCommand，它可以區分 HTTP 或 WS
        if (sendCommand) {
             // App 會有自己的暫存 logs 陣列處理機制
             sendCommand(cmd);
        }
    };

    return (
        <div className="flex-1 glass-panel rounded-2xl p-0 flex flex-col overflow-hidden">
            {/* 標題列 */}
            <div className="h-14 border-b border-white/10 flex items-center px-6 shrink-0">
                <i className="fas fa-terminal text-success mr-3"></i>
                <h2 className="text-white font-semibold flex items-center gap-3">
                    伺服器終端機
                    {isConnected ? (
                        <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full border border-green-500/30">即時同步中</span>
                    ) : (
                        <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded-full border border-yellow-500/30">中斷連線</span>
                    )}
                </h2>
            </div>

            {/* 日誌區 */}
            <div className="flex-1 overflow-y-auto p-4 font-mono text-sm space-y-1 custom-scrollbar bg-black/20">
                {displayLogs.map((log) => (
                    <div key={log.id} className="flex gap-2">
                        {log.time && <span className="text-slate-600 shrink-0">[{log.time}]</span>}
                        <span className={
                            log.level === 'CMD' ? 'text-cyan-400' :
                                log.level === 'ERROR' ? 'text-red-400' :
                                    'text-slate-300'
                        } dangerouslySetInnerHTML={{ __html: log.message }} />
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
