export default function Dashboard({ serverStatus, cpuUsage, ramUsage, activePlayers, maxPlayers, onStart, onStop }) {
    const isOnline = serverStatus === 'Online';
    return (
        <div className="flex flex-col xl:flex-row gap-4 h-auto xl:h-48 shrink-0">
            {/* Server Status Card */}
            <div className="flex-1 glass-panel rounded-3xl p-6 flex flex-col justify-between relative overflow-hidden group">
                <div className="absolute -right-10 -top-10 w-40 h-40 bg-primary/20 blur-[50px] rounded-full group-hover:bg-primary/30 transition-all duration-500"></div>
                <div className="flex justify-between items-start z-10">
                    <div>
                        <h2 className="text-2xl font-bold text-white tracking-tight">BlockRealms Web Panel</h2>
                        <div className="flex items-center gap-2 mt-1">
                            <span className="relative flex h-3 w-3">
                                {isOnline && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>}
                                <span className={\`relative inline-flex rounded-full h-3 w-3 \${isOnline ? 'bg-green-500' : 'bg-red-500'}\`}></span>
                        </span>
                        <span className={\`font-medium text-sm \${isOnline ? 'text-green-400' : 'text-red-400'}\`}>{serverStatus}</span>
                    <span className="text-slate-500 text-sm mx-1">•</span>
                    <span className="text-slate-400 text-sm">v1.20.71 (Paper)</span>
                </div>
            </div>
            <div className="px-3 py-1 rounded-full bg-white/5 border border-white/10">
                <span className="text-xs font-mono text-slate-300">ID: #8291-MZK</span>
            </div>
        </div>

        {/* Resources */ }
        <div className="flex flex-wrap gap-8 mt-6 z-10">
          <div className="flex items-center gap-4">
            <div className="relative w-16 h-16">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                <path className="text-white/10" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3"></path>
                <path className="text-primary drop-shadow-[0_0_3px_rgba(238,43,140,0.8)]" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeDasharray={\`\${cpuUsage}, 100\`} strokeLinecap="round" strokeWidth="3"></path>
              </svg>
              <div className="absolute inset-0 flex items-center justify-center flex-col">
                <span className="text-sm font-bold text-white">{cpuUsage}%</span>
              </div>
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-medium text-slate-300">CPU Load</span>
              <span className="text-xs text-slate-500">3.2 GHz</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative w-16 h-16">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                <path className="text-white/10" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3"></path>
                <path className="text-secondary drop-shadow-[0_0_3px_rgba(244,114,182,0.8)]" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeDasharray={\`\${ramUsage}, 100\`} strokeLinecap="round" strokeWidth="3"></path>
              </svg>
              <div className="absolute inset-0 flex items-center justify-center flex-col">
                <span className="text-sm font-bold text-white">{ramUsage}%</span>
              </div>
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-medium text-slate-300">RAM Usage</span>
              <span className="text-xs text-slate-500">23GB / 32GB</span>
            </div>
          </div >
        </div >
      </div >

        {/* Action Buttons & Quick Stats */ }
        < div className = "w-full xl:w-80 flex flex-col gap-4 shrink-0" >
        <div className="glass-panel rounded-3xl p-4 flex gap-3 h-1/2 items-center justify-center">
          <button onClick={onStart} className="group relative flex-1 h-full rounded-2xl bg-gradient-to-br from-green-500/20 to-emerald-600/20 border border-green-500/30 text-green-400 font-bold hover:scale-[1.02] active:scale-[0.98] transition-all flex flex-col items-center justify-center gap-2 shadow-[0_4px_20px_-5px_rgba(34,197,94,0.3)] min-h-[80px]">
            <span className="material-symbols-outlined text-3xl drop-shadow-[0_0_10px_rgba(74,222,128,0.5)]">play_arrow</span>
            Start
          </button>
          <button onClick={onStop} className="group relative flex-1 h-full rounded-2xl bg-gradient-to-br from-red-500/20 to-rose-600/20 border border-red-500/30 text-red-400 font-bold hover:scale-[1.02] active:scale-[0.98] transition-all flex flex-col items-center justify-center gap-2 shadow-[0_4px_20px_-5px_rgba(239,68,68,0.3)] min-h-[80px]">
            <span className="material-symbols-outlined text-3xl drop-shadow-[0_0_10px_rgba(248,113,113,0.5)]">stop</span>
            Stop
          </button>
        </div>
        <div className="glass-panel rounded-3xl p-4 h-1/2 flex items-center justify-between px-6 min-h-[80px]">
          <div className="flex flex-col">
            <span className="text-slate-400 text-sm font-medium">Active Players</span>
            <span className="text-2xl font-bold text-white">{activePlayers} <span className="text-slate-500 text-lg">/ {maxPlayers}</span></span>
          </div>
          <div className="flex -space-x-3">
            <div className="w-10 h-10 rounded-full border-2 border-[#2a1a22] bg-primary/20 flex items-center justify-center text-xs font-bold text-white">+{activePlayers}</div>
          </div>
        </div>
      </div >
    </div >
  );
}
