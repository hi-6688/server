export default function LiveConsole({ logs, commandInput, setCommandInput, onSendCommand }) {
    return (
    <div className="flex-1 glass-panel rounded-3xl p-0 flex flex-col overflow-hidden min-h-[400px]">
      <div className="h-14 border-b border-white/5 flex items-center justify-between px-6 bg-black/20 shrink-0">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-slate-400">terminal</span>
          <span className="font-medium text-slate-300">Live Console</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/30 border border-white/5">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            <span className="text-xs text-slate-400 font-mono">Connected</span>
          </div>
        </div>
      </div>

      <div className="flex-1 p-6 font-mono text-sm overflow-y-auto custom-scrollbar bg-[#0a0508]/40">
        <div className="flex flex-col gap-1.5">
          {logs.map((log, index) => (
            <div key={index} className="flex gap-3">
              <span className="text-slate-500 shrink-0">[{log.time}]</span>
              <span className={\`shrink-0 \${log.level === 'WARN' ? 'text-yellow-400' : log.level === 'ERROR' ? 'text-red-400' : 'text-blue-400'}\`}>[{log.level}]</span>
              <span className="text-slate-300" dangerouslySetInnerHTML={{ __html: log.message }}></span>
            </div>
          ))}
        </div>
      </div>

      <div className="h-16 p-4 bg-black/20 border-t border-white/5 shrink-0">
        <div className="flex items-center gap-3 w-full h-full bg-white/5 rounded-xl px-4 border border-white/5 focus-within:border-primary/50 focus-within:bg-white/10 transition-colors">
          <span className="text-primary font-bold text-lg">&gt;_</span>
          <input 
            className="bg-transparent border-none outline-none text-white w-full h-full focus:ring-0 placeholder:text-slate-500 font-mono text-sm" 
            placeholder="Type a command..." 
            type="text" 
            value={commandInput}
            onChange={(e) => setCommandInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                onSendCommand();
              }
            }}
          />
          <button onClick={onSendCommand} className="text-slate-400 hover:text-primary transition-colors">
            <span className="material-symbols-outlined">send</span>
          </button>
        </div>
      </div>
    </div >
  );
}
