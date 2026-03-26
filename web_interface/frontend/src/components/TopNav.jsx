// TopNav.jsx — 頂部雙層導航列 (還原舊版 admin.html 的頂部導航)
export default function TopNav({
    activeTab = 'dashboard',
    onTabChange = () => { },
    serverStatus = '離線',
    isOnline = false,
    vm2Online = false,
    wsConnected = false,
    instances = [],
    currentInstance = 'main',
    onInstanceChange = () => { },
    onDeleteInstance = () => { },
    onOpenCreateModal = () => { }
}) {
    // 導航項目定義 (與舊版一致)
    const tabs = [
        { id: 'dashboard', icon: 'dashboard', label: '儀表板' },
        { id: 'settings', icon: 'settings', label: '設定' },
        { id: 'worlds', icon: 'public', label: '世界' },
        { id: 'files', icon: 'folder_open', label: '檔案' },
        { id: 'gamerules', icon: 'gavel', label: '規則' },
        { id: 'addons', icon: 'extension', label: '模組' },
        { id: 'players', icon: 'group', label: '玩家' },
    ];

    const handleDelete = (e, uuid) => {
        e.stopPropagation();
        onDeleteInstance(uuid);
    };

    return (
        <div className="w-full fixed top-0 left-0 z-50 flex flex-col shadow-lg">
            {/* 第一層：主導航 */}
            <nav className="w-full transition-all duration-300 bg-black/30 border-b border-white/10">
                <div className="max-w-7xl mx-auto w-full px-3 sm:px-6 py-2 sm:py-3 flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4">
                    {/* Logo 與名稱 */}
                    <div className="flex items-center gap-3 w-full sm:w-auto justify-start">
                        <div className="relative shrink-0">
                            <div className="w-10 h-10 sm:w-12 sm:h-12 flex items-center justify-center bg-gradient-to-br from-black/40 to-white/5 rounded-xl border border-white/10 shadow-[0_0_15px_rgba(0,0,0,0.3)] p-1 sm:p-1.5 overflow-visible">
                                <img src="/cover.png" alt="Server Logo" className="w-full h-full object-contain drop-shadow-lg scale-110 hover:scale-125 transition-transform duration-300" style={{ imageRendering: 'pixelated' }} />
                            </div>
                            <div className={`absolute -bottom-1 -right-1 w-3.5 h-3.5 sm:w-4 sm:h-4 rounded-full border-[2.5px] border-[#1e1e1e] z-10 transition-colors duration-500 ${vm2Online ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]'}`} title={vm2Online ? "VM2 系統運作中" : "VM2 系統離線"}></div>
                        </div>
                        <div className="flex flex-col">
                            <h1 className="text-white text-base sm:text-lg font-bold truncate">麥亂伺服器</h1>
                            <p className={`text-[10px] sm:text-xs font-bold uppercase tracking-wider ${isOnline ? 'text-green-400 drop-shadow-[0_0_8px_rgba(74,222,128,0.5)]' : 'text-secondary/80'}`}>
                                {serverStatus}
                            </p>
                        </div>
                    </div>

                    {/* 導航連結 */}
                    <div className="flex items-center justify-between sm:justify-center gap-1 sm:gap-2 lg:gap-4 w-full sm:w-auto px-1 sm:px-2 pt-1 sm:pt-0">
                        {tabs.map((tab) => (
                            <a
                                key={tab.id}
                                className={`group relative flex flex-col sm:flex-row items-center justify-center gap-1 sm:gap-2 p-1.5 sm:px-4 sm:py-2.5 rounded-xl cursor-pointer transition-all flex-1 sm:flex-none ${activeTab === tab.id
                                    ? 'nav-link-active bg-white/5'
                                    : 'nav-link hover:bg-white/5'
                                    }`}
                                onClick={() => onTabChange(tab.id)}
                            >
                                <span className={`material-symbols-outlined text-xl sm:text-lg transition-all duration-300 ${activeTab === tab.id
                                    ? 'text-primary drop-shadow-[0_0_8px_rgba(238,43,140,0.7)]'
                                    : 'text-white/60 group-hover:text-secondary'
                                    }`}>
                                    {tab.icon}
                                </span>
                                <span className={`font-medium text-[10px] sm:text-sm mt-0.5 sm:mt-0 transition-colors hidden sm:block ${activeTab === tab.id ? 'text-white' : 'text-white/60 group-hover:text-white/90'}`}>{tab.label}</span>
                                {/* 底部/頂部 亮線 indicator */}
                                {activeTab === tab.id && (
                                    <span className="absolute bottom-0 left-2 right-2 h-[2px] rounded-full bg-primary shadow-[0_0_8px_rgba(238,43,140,0.6)]"></span>
                                )}
                            </a>
                        ))}
                    </div>

                    {/* 右側：可預留給未來的使用者選單或登出按鈕，目前為空以保持簡潔 */}
                    <div className="flex items-center gap-4">
                    </div>
                </div>
            </nav>

            {/* 第二層：伺服器列表與控制 */}
            <div className="w-full transition-all duration-300 bg-black/30 border-b border-white/10">
                <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-2 sm:py-3 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2 sm:gap-4 w-full sm:w-auto">
                        <div className="font-bold text-white uppercase tracking-widest whitespace-nowrap hidden sm:block">伺服器列表</div>
                        <div className="flex items-center gap-2">
                            {instances.map(inst => (
                                <div key={inst.uuid} className="relative group">
                                    <button
                                        onClick={() => onInstanceChange(inst.uuid)}
                                        className={`pl-3 pr-4 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap border ${currentInstance === inst.uuid ? 'bg-primary/20 border-primary text-white shadow-[0_0_10px_rgba(238,43,140,0.5)]' : 'bg-white/5 border-white/10 text-white/70 hover:bg-white/10 hover:text-white'}`}
                                    >
                                        {inst.name}
                                    </button>
                                    {inst.uuid !== 'main' && (
                                        <button 
                                            onClick={(e) => handleDelete(e, inst.uuid)}
                                            className="absolute -top-1 -right-1 w-5 h-5 bg-red-500/80 text-white rounded-full flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 hover:bg-red-500 transition-all"
                                            title="刪除實例"
                                        >
                                            <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>close</span>
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                    <div className="shrink-0 ml-auto sm:ml-4 flex items-center gap-2">
                        {/* 伺服器列表在手機版保留獨立按鈕 */}
                        <button
                            onClick={onOpenCreateModal}
                            className="px-3 py-1.5 sm:px-4 sm:py-2 rounded-xl bg-green-500/20 border border-white/20 text-green-400 hover:bg-green-500/40 transition-colors whitespace-nowrap flex items-center gap-1">
                            <i className="fas fa-plus sm:hidden text-xs"></i>
                            <span className="hidden sm:inline">+ 新增</span>
                        </button>
                    </div>
                </div >
            </div >
        </div >
    );
}
