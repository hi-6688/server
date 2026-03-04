// TopNav.jsx — 頂部雙層導航列 (還原舊版 admin.html 的頂部導航)
export default function TopNav({ activeTab = 'dashboard', onTabChange = () => { } }) {
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
                            <div
                                className="w-10 h-10 rounded-full bg-cover bg-center border-2 border-primary/30 shadow-[0_0_15px_rgba(238,43,140,0.3)]"
                                style={{ backgroundImage: 'url("https://avatars.githubusercontent.com/u/9919?v=4")' }}
                            ></div>
                            <div className="absolute bottom-0 right-0 w-3 h-3 rounded-full bg-green-500 border-2 border-black/60 status-dot-online"></div>
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
                </div>
            </nav>

            {/* 第二層：伺服器列表 */}
            <div className="w-full transition-all duration-300 bg-black/30 border-b border-white/10">
                <div className="max-w-7xl mx-auto w-full px-6 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="font-bold text-white uppercase tracking-widest whitespace-nowrap">伺服器列表</div>
                        <button className="px-4 py-2 rounded-xl bg-green-500/20 border border-white/20 text-green-400 hover:bg-green-500/40 transition-colors whitespace-nowrap">
                            + 新增
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
