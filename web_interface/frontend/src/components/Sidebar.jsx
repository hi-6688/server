export default function Sidebar() {
    return (
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
    );
}
