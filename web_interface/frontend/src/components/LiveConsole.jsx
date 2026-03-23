// LiveConsole.jsx — 嵌入式即時日誌 (舊版配色)
import { useEffect, useRef } from 'react';

export default function LiveConsole({ logs, commandInput, setCommandInput, onSendCommand, wsConnected = false }) {
  const logsContainerRef = useRef(null);

  // 只在日誌容器內部捲動，不影響整個頁面
  useEffect(() => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [logs]);

  // 根據日誌等級決定顏色
  const getLevelColor = (level) => {
    switch (level) {
      case 'INFO': return 'text-green-400';
      case 'WARN': return 'text-yellow-400';
      case 'ERROR': return 'text-red-400';
      case 'CMD': return 'text-cyan-400';
      case 'Chat': return 'text-white';
      default: return 'text-slate-300';
    }
  };

  return (
    <div className="glass-panel rounded-2xl flex flex-col overflow-hidden mt-4">
      {/* 標題列 */}
      <div className="h-12 border-b border-white/10 flex items-center px-4 shrink-0">
        <i className="fas fa-terminal text-success mr-3"></i>
        <h3 className="text-white font-semibold text-sm">Live Console</h3>
        <span className={`ml-auto flex items-center gap-2 text-xs ${wsConnected ? 'text-green-400' : 'text-yellow-400'}`}>
          <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.5)] animate-pulse' : 'bg-yellow-400 shadow-[0_0_8px_rgba(250,204,21,0.5)] animate-ping'}`}></div>
          {wsConnected ? 'Connected' : 'Reconnecting...'}
        </span>
      </div>

      {/* 日誌區 */}
      <div ref={logsContainerRef} className="h-48 overflow-y-auto p-3 font-mono text-xs space-y-0.5 custom-scrollbar bg-black/20">
        {logs.map((log, i) => (
          <div key={i} className="flex gap-2">
            {log.time && <span className="text-slate-600 shrink-0">[{log.time}]</span>}
            <span className={`${getLevelColor(log.level)} font-medium shrink-0`}>[{log.level}]</span>
            <span className="text-slate-300" dangerouslySetInnerHTML={{ __html: log.message }} />
          </div>
        ))}
      </div>

      {/* 指令輸入 */}
      <div className="h-10 border-t border-white/10 flex items-center px-3 gap-2 shrink-0">
        <span className="text-success font-mono text-sm">$</span>
        <input
          type="text"
          value={commandInput}
          onChange={(e) => setCommandInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSendCommand()}
          placeholder="輸入伺服器指令..."
          className="flex-1 bg-transparent text-white placeholder:text-slate-600 outline-none font-mono text-xs"
        />
        <button
          onClick={onSendCommand}
          className="px-3 py-1 rounded-lg bg-success/20 text-success hover:bg-success/30 transition-all text-xs font-medium"
        >
          送出
        </button>
      </div>
    </div>
  );
}
