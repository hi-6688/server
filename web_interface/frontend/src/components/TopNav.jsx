// TopNav.jsx — 頂部雙層導航列 (還原舊版 admin.html 的頂部導航)
export default function TopNav({
    activeTab = 'dashboard',
    onTabChange = () => { },
    isOnline = false,
    wsConnected = false,
    instances = [],
    currentInstance = 'main',
    onInstanceChange = () => { }
}) {
    // 導航項目定義 (與舊版一致)
    const tabs = [
        { id: 'dashboard', icon: 'dashboard', label: '儀表板' },
        { id: 'settings', icon: 'settings', label: '設定' },
        { id: 'files', icon: 'public', label: '世界' },
        { id: 'gamerules', icon: 'gavel', label: '規則' },
        { id: 'players', icon: 'group', label: '玩家' },
    ];

    return (
        <div className="w-full fixed top-0 left-0 z-50 flex flex-col shadow-lg">
            {/* 第一層：主導航 */}
            <nav className="w-full transition-all duration-300 bg-black/30 border-b border-white/10">
                <div className="max-w-7xl mx-auto w-full px-6 py-3 flex items-center justify-between">
                    {/* Logo 與名稱 */}
                    <div className="flex items-center gap-4">
                        <div className="relative shrink-0">
                            <div className="w-12 h-12 flex items-center justify-center bg-gradient-to-br from-black/40 to-white/5 rounded-xl border border-white/10 shadow-[0_0_15px_rgba(0,0,0,0.3)] p-1.5 overflow-visible">
                                <img src="/cover.png" alt="Server Logo" className="w-full h-full object-contain drop-shadow-lg scale-110 hover:scale-125 transition-transform duration-300" style={{ imageRendering: 'pixelated' }} />
                            </div>
                            <div className={`absolute -bottom-1 -right-1 w-4 h-4 rounded-full border-[2.5px] border-[#1e1e1e] z-10 transition-colors duration-500 ${isOnline ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]'}`}></div>
                        </div>
                        <div className="hidden sm:flex flex-col">
                            <h1 className="text-white text-lg font-bold truncate">麥亂伺服器</h1>
                            <p className="text-secondary/80 text-[10px] sm:text-xs font-medium uppercase tracking-wider">
                                Superuser
                            </p>
                        </div>
                    </div>

                    {/* 導航連結 */}
                    <div className="flex items-center gap-2 lg:gap-4 overflow-x-auto custom-scrollbar px-2">
                        {tabs.map((tab) => (
                            <a
                                key={tab.id}
                                className={`group relative flex items-center gap-2 px-4 py-2.5 rounded-xl cursor-pointer transition-all whitespace-nowrap ${activeTab === tab.id
                                    ? 'nav-link-active'
                                    : 'nav-link'
                                    }`}
                                onClick={() => onTabChange(tab.id)}
                            >
                                <span className={`material-symbols-outlined text-lg transition-all duration-300 ${activeTab === tab.id
                                    ? 'text-primary drop-shadow-[0_0_8px_rgba(238,43,140,0.7)]'
                                    : 'group-hover:text-secondary'
                                    }`}>
                                    {tab.icon}
                                </span>
                                <span className={`font-medium text-sm transition-colors ${activeTab === tab.id ? 'text-white' : ''}`}>{tab.label}</span>
                                {/* 底部亮線 indicator */}
                                {activeTab === tab.id && (
                                    <span className="absolute bottom-0 left-2 right-2 h-[2px] rounded-full bg-primary shadow-[0_0_8px_rgba(238,43,140,0.6)]"></span>
                                )}
                            </a>
                        ))}
                    </div>

                    {/* 右側：WebSocket 狀態與設定 (或未來的使用者頭像) */}
                    <div className="flex items-center gap-4">
                        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-black/40 border border-white/5 backdrop-blur-sm">
                            <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.5)] animate-pulse' : 'bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.5)]'}`}></div>
                            <span className={`text-[10px] font-medium tracking-wide ${wsConnected ? 'text-green-400/90' : 'text-red-400/90'}`}>
                                {wsConnected ? 'LIVE' : 'HTTP'}
                            </span>
                        </div>
                    </div>
                </div>
            </nav>

            {/* 第二層：伺服器列表 */}
            <div className="w-full transition-all duration-300 bg-black/30 border-b border-white/10">
                <div className="max-w-7xl mx-auto w-full px-6 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-4 overflow-x-auto custom-scrollbar">
                        <div className="font-bold text-white uppercase tracking-widest whitespace-nowrap hidden sm:block">伺服器列表</div>
                        <div className="flex items-center gap-2">
                            {instances.map(inst => (
                                <button
                                    key={inst.uuid}
                                    onClick={() => onInstanceChange(inst.uuid)}
                                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap border ${currentInstance === inst.uuid ? 'bg-primary/20 border-primary text-white shadow-[0_0_10px_rgba(238,43,140,0.5)]' : 'bg-white/5 border-white/10 text-white/70 hover:bg-white/10 hover:text-white'}`}
                                >
                                    {inst.name}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div className="shrink-0 ml-4 hidden md:block">
                        <button className="px-4 py-2 rounded-xl bg-green-500/20 border border-white/20 text-green-400 hover:bg-green-500/40 transition-colors whitespace-nowrap">
                            + 新增
                        </button>
                    </div>
                </div >
            </div >
        </div >
    );
}
