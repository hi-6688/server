import { useState, useEffect } from 'react';

function App() {
  const [logs, setLogs] = useState([]);
  const [cpuUsage, setCpuUsage] = useState(45);
  const [ramUsage, setRamUsage] = useState(72);

  return (
    <div className="font-display text-slate-100 antialiased h-screen overflow-hidden selection:bg-primary selection:text-white relative">
      <style dangerouslySetInnerHTML={{
        __html: `
        .custom-scrollbar::-webkit-scrollbar { width: 8px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.2); border-radius: 4px; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(238, 43, 140, 0.3); border-radius: 4px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(238, 43, 140, 0.5); }
        .glass-panel {
            background: rgba(20, 10, 15, 0.65);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-top: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        }
        .glass-button {
            background: rgba(238, 43, 140, 0.15);
            border: 1px solid rgba(238, 43, 140, 0.3);
            transition: all 0.2s ease;
        }
        .glass-button:hover {
            background: rgba(238, 43, 140, 0.25);
            box-shadow: 0 0 15px rgba(238, 43, 140, 0.3);
            transform: translateY(-1px);
        }
        .status-dot { box-shadow: 0 0 10px currentColor; }
        .bg-cherry-blossom {
            background-image: url('https://images.unsplash.com/photo-1524230507669-5ff97982bb5e?q=80&w=2838&auto=format&fit=crop');
        }
      `}} />

      {/* Background Image Layer */}
      <div className="fixed inset-0 z-0 bg-cherry-blossom bg-cover bg-center">
        <div className="absolute inset-0 bg-[#120810]/70"></div>
      </div>

      {/* Main Layout */}
      <div className="relative z-10 flex flex-col lg:flex-row h-full w-full p-4 gap-4">

        {/* Sidebar Navigation */}
        <aside className="w-full lg:w-72 flex flex-col justify-between glass-panel rounded-3xl p-4 transition-all duration-300 shrink-0">
          <div className="flex flex-col gap-6">
            <div className="flex items-center gap-4 px-2 py-2">
              <div className="relative shrink-0">
                <div
                  className="w-12 h-12 rounded-full bg-cover bg-center border-2 border-primary/30 shadow-[0_0_15px_rgba(238,43,140,0.3)]"
                  style={{ backgroundImage: 'url("https://avatars.githubusercontent.com/u/9919?v=4")' }}
                ></div>
                <div className="absolute bottom-0 right-0 w-3 h-3 rounded-full bg-green-500 border-2 border-[#181114] status-dot text-green-500"></div>
              </div>
              <div className="hidden lg:flex flex-col overflow-hidden">
                <h1 className="text-white text-lg font-bold truncate">Mizuki Admin</h1>
                <p className="text-secondary/80 text-xs font-medium uppercase tracking-wider">Superuser</p>
              </div>
            </div>

            <nav className="flex flex-col gap-2 mt-4 overflow-y-auto">
              <a className="group flex items-center gap-4 px-3 py-3 rounded-2xl bg-primary/20 text-white border border-primary/20 shadow-[0_0_10px_rgba(238,43,140,0.1)] transition-all hover:bg-primary/30" href="#">
                <span className="material-symbols-outlined text-primary group-hover:text-white transition-colors">dashboard</span>
                <span className="font-medium">Dashboard</span>
              </a>
              <a className="group flex items-center gap-4 px-3 py-3 rounded-2xl text-slate-300 hover:bg-white/5 hover:text-white transition-all" href="#">
                <span className="material-symbols-outlined group-hover:text-secondary transition-colors">terminal</span>
                <span className="font-medium">Console</span>
              </a>
              <a className="group flex items-center gap-4 px-3 py-3 rounded-2xl text-slate-300 hover:bg-white/5 hover:text-white transition-all" href="#">
                <span className="material-symbols-outlined group-hover:text-secondary transition-colors">group</span>
                <span className="font-medium">Players</span>
              </a>
              <a className="group flex items-center gap-4 px-3 py-3 rounded-2xl text-slate-300 hover:bg-white/5 hover:text-white transition-all" href="#">
                <span className="material-symbols-outlined group-hover:text-secondary transition-colors">folder_open</span>
                <span className="font-medium">Files</span>
              </a>
              <a className="group flex items-center gap-4 px-3 py-3 rounded-2xl text-slate-300 hover:bg-white/5 hover:text-white transition-all" href="#">
                <span className="material-symbols-outlined group-hover:text-secondary transition-colors">settings</span>
                <span className="font-medium">Settings</span>
              </a>
            </nav>
          </div>

          <div className="flex flex-col gap-2 mt-4">
            <button className="flex items-center gap-4 px-3 py-3 rounded-2xl text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-all w-full">
              <span className="material-symbols-outlined">logout</span>
              <span className="font-medium">Logout</span>
            </button>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col gap-4 overflow-hidden">

          {/* Top Bar: Status & Actions */}
          <div className="flex flex-col xl:flex-row gap-4 h-auto xl:h-48 shrink-0">
            {/* Server Status Card */}
            <div className="flex-1 glass-panel rounded-3xl p-6 flex flex-col justify-between relative overflow-hidden group">
              <div className="absolute -right-10 -top-10 w-40 h-40 bg-primary/20 blur-[50px] rounded-full group-hover:bg-primary/30 transition-all duration-500"></div>
              <div className="flex justify-between items-start z-10">
                <div>
                  <h2 className="text-2xl font-bold text-white tracking-tight">BlockRealms Web Panel</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="relative flex h-3 w-3">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                    </span>
                    <span className="text-green-400 font-medium text-sm">Online</span>
                    <span className="text-slate-500 text-sm mx-1">•</span>
                    <span className="text-slate-400 text-sm">v1.20.71 (Paper)</span>
                  </div>
                </div>
                <div className="px-3 py-1 rounded-full bg-white/5 border border-white/10">
                  <span className="text-xs font-mono text-slate-300">ID: #8291-MZK</span>
                </div>
              </div>

              {/* Resources */}
              <div className="flex flex-wrap gap-8 mt-6 z-10">
                <div className="flex items-center gap-4">
                  <div className="relative w-16 h-16">
                    <svg className="w-full h-full -rotate-90" viewBox="0 0 36 36">
                      <path className="text-white/10" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3"></path>
                      <path className="text-primary drop-shadow-[0_0_3px_rgba(238,43,140,0.8)]" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeDasharray={`${cpuUsage}, 100`} strokeLinecap="round" strokeWidth="3"></path>
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
                      <path className="text-secondary drop-shadow-[0_0_3px_rgba(244,114,182,0.8)]" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeDasharray={`${ramUsage}, 100`} strokeLinecap="round" strokeWidth="3"></path>
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center flex-col">
                      <span className="text-sm font-bold text-white">{ramUsage}%</span>
                    </div>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-slate-300">RAM Usage</span>
                    <span className="text-xs text-slate-500">23GB / 32GB</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Action Buttons & Quick Stats */}
            <div className="w-full xl:w-80 flex flex-col gap-4 shrink-0">
              <div className="glass-panel rounded-3xl p-4 flex gap-3 h-1/2 items-center justify-center">
                <button className="group relative flex-1 h-full rounded-2xl bg-gradient-to-br from-green-500/20 to-emerald-600/20 border border-green-500/30 text-green-400 font-bold hover:scale-[1.02] active:scale-[0.98] transition-all flex flex-col items-center justify-center gap-2 shadow-[0_4px_20px_-5px_rgba(34,197,94,0.3)] min-h-[80px]">
                  <span className="material-symbols-outlined text-3xl drop-shadow-[0_0_10px_rgba(74,222,128,0.5)]">play_arrow</span>
                  Start
                </button>
                <button className="group relative flex-1 h-full rounded-2xl bg-gradient-to-br from-red-500/20 to-rose-600/20 border border-red-500/30 text-red-400 font-bold hover:scale-[1.02] active:scale-[0.98] transition-all flex flex-col items-center justify-center gap-2 shadow-[0_4px_20px_-5px_rgba(239,68,68,0.3)] min-h-[80px]">
                  <span className="material-symbols-outlined text-3xl drop-shadow-[0_0_10px_rgba(248,113,113,0.5)]">stop</span>
                  Stop
                </button>
              </div>
              <div className="glass-panel rounded-3xl p-4 h-1/2 flex items-center justify-between px-6 min-h-[80px]">
                <div className="flex flex-col">
                  <span className="text-slate-400 text-sm font-medium">Active Players</span>
                  <span className="text-2xl font-bold text-white">12 <span className="text-slate-500 text-lg">/ 50</span></span>
                </div>
                <div className="flex -space-x-3">
                  <div className="w-10 h-10 rounded-full border-2 border-[#2a1a22] bg-primary/20 flex items-center justify-center text-xs font-bold text-white">+12</div>
                </div>
              </div>
            </div>
          </div>

          {/* Terminal Console Area */}
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
                <div className="flex gap-3">
                  <span className="text-slate-500 shrink-0">[14:20:01]</span>
                  <span className="text-blue-400 shrink-0">[INFO]</span>
                  <span className="text-slate-300">Starting minecraft server version 1.20.71</span>
                </div>
                <div className="flex gap-3">
                  <span className="text-slate-500 shrink-0">[14:20:02]</span>
                  <span className="text-blue-400 shrink-0">[INFO]</span>
                  <span className="text-slate-300">Loading properties</span>
                </div>
                <div className="flex gap-3">
                  <span className="text-slate-500 shrink-0">[14:20:05]</span>
                  <span className="text-blue-400 shrink-0">[INFO]</span>
                  <span className="text-slate-300">Preparing level "world"</span>
                </div>
                <div className="flex gap-3">
                  <span className="text-slate-500 shrink-0">[14:20:08]</span>
                  <span className="text-yellow-400 shrink-0">[WARN]</span>
                  <span className="text-slate-300">Can't keep up! Is the server overloaded?</span>
                </div>
                <div className="flex gap-3">
                  <span className="text-slate-500 shrink-0">[14:20:15]</span>
                  <span className="text-blue-400 shrink-0">[INFO]</span>
                  <span className="text-slate-300">Player joined the game</span>
                </div>
                <div className="flex gap-3">
                  <span className="text-slate-500 shrink-0">[14:20:22]</span>
                  <span className="text-green-400 shrink-0">[Chat]</span>
                  <span className="text-slate-300"><span className="text-white font-bold">&lt;Admin&gt;</span> The cherry blossoms are blooming! 🌸</span>
                </div>
                <div className="flex gap-3">
                  <span className="text-slate-500 shrink-0">[14:21:05]</span>
                  <span className="text-blue-400 shrink-0">[INFO]</span>
                  <span className="text-slate-300">Saving chunks for level 'ServerLevel'...</span>
                </div>
              </div>
            </div>

            <div className="h-16 p-4 bg-black/20 border-t border-white/5 shrink-0">
              <div className="flex items-center gap-3 w-full h-full bg-white/5 rounded-xl px-4 border border-white/5 focus-within:border-primary/50 focus-within:bg-white/10 transition-colors">
                <span className="text-primary font-bold text-lg">&gt;_</span>
                <input className="bg-transparent border-none outline-none text-white w-full h-full focus:ring-0 placeholder:text-slate-500 font-mono text-sm" placeholder="Type a command..." type="text" />
                <button className="text-slate-400 hover:text-primary transition-colors">
                  <span className="material-symbols-outlined">send</span>
                </button>
              </div>
            </div>
          </div>

        </main>
      </div>
    </div>
  );
}

export default App;
