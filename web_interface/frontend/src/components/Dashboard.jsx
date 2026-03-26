// Dashboard.jsx — 還原舊版儀表板：狀態區 + 8 張資訊卡片 (單欄)
export default function Dashboard({
  serverStatus, isOnline, activePlayers, maxPlayers, version,
  cpuLoad, ramPercent, ramUsed, ramTotal,
  diskPercent, diskUsed, diskTotal, netRx, netTx,
  onStart, onStop, onRestart, publicIp
}) {
  return (
    <div className="flex flex-col gap-4">
      {/* 伺服器狀態區 */}
      <div className="glass-panel p-4 sm:p-6 rounded-2xl flex flex-col sm:flex-row items-center sm:justify-between text-center sm:text-left gap-4">
        <div className="flex flex-col sm:flex-row items-center gap-3 sm:gap-6">
          <h2 className="text-lg sm:text-xl font-bold text-white whitespace-nowrap">伺服器狀態</h2>
          <div className="flex gap-3">
          {/* 玩家人數徽章 */}
          <div className="status-badge">
            <i className="fas fa-users text-[10px] text-text-sub"></i>
            <span>{activePlayers} / {maxPlayers}</span>
          </div>
          {/* 線上/離線徽章 */}
          <div className="status-badge">
            <div className={`status-dot ${isOnline ? 'status-dot-online' : 'status-dot-offline'}`}></div>
            <span>{serverStatus}</span>
          </div>
        </div>
        </div>
        {/* 電源按鈕 */}
        <div className="flex gap-3 sm:gap-4 shrink-0 mt-2 sm:mt-0">
          {isOnline ? (
            <button className="btn-power btn-power-stop" onClick={onStop}>
              <i className="fas fa-power-off"></i>
              <span className="ml-2">關閉</span>
            </button>
          ) : (
            <button className="btn-power" onClick={onStart}>
              <i className="fas fa-power-off"></i>
              <span className="ml-2">啟動</span>
            </button>
          )}
          <button className="btn-power btn-power-restart" onClick={onRestart}>
            <i className="fas fa-sync-alt"></i>
            <span className="ml-2">重啟</span>
          </button>
        </div>
      </div>

      {/* 資訊卡片 Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* 1. 加入伺服器連結 (強制兩欄至三欄寬，因為網址較長) */}
        <div className="glass-panel p-4 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-3 col-span-1 md:col-span-2 lg:col-span-3">
          <div className="font-bold text-text-sub">
            <i className="fas fa-share-alt mr-2"></i>加入伺服器連結
          </div>
          <div className="flex items-center gap-2 flex-1 justify-end">
            <span className="font-mono text-sm text-white/90 bg-black/30 px-3 py-2 rounded-md border border-white/10 truncate max-w-full flex-1 shadow-[inset_0_2px_4px_rgba(0,0,0,0.5)]">
              {window.location.origin}/join.html
            </span>
            <div className="flex shrink-0 gap-2">
              <button className="btn-action shrink-0" onClick={() => navigator.clipboard.writeText(window.location.origin + '/join.html')}>
                <i className="fas fa-copy"></i> <span className="hidden sm:inline">複製</span>
              </button>
              <a className="btn-action shrink-0" href="/join.html" target="_blank" rel="noreferrer">
                <i className="fas fa-external-link-alt"></i> <span className="hidden sm:inline">開啟</span>
              </a>
            </div>
          </div>
        </div>

        {/* 2. 伺服器 IP */}
        <div className="glass-panel p-3 sm:p-4 rounded-2xl flex items-center justify-between">
          <div className="font-bold text-text-sub">
            <i className="fas fa-network-wired mr-2"></i>伺服器 IP (Address)
          </div>
          <span className="font-mono text-base text-white">{publicIp || '載入中...'}</span>
        </div>

        {/* 3. 連接埠 */}
        <div className="glass-panel p-3 sm:p-4 rounded-2xl flex items-center justify-between">
          <div className="font-bold text-text-sub">
            <i className="fas fa-door-open mr-2"></i>連接埠 (Port)
          </div>
          <span className="font-mono text-base text-primary">19132</span>
        </div>

        {/* 4. 軟體 */}
        <div className="glass-panel p-3 sm:p-4 rounded-2xl flex items-center justify-between">
          <div className="font-bold text-text-sub">
            <i className="fas fa-microchip mr-2"></i>軟體 (Software)
          </div>
          <span className="font-bold">Bedrock Dedicated Server</span>
        </div>

        {/* 5. 版本 */}
        <div className="glass-panel p-3 sm:p-4 rounded-2xl flex items-center justify-between">
          <div className="font-bold text-text-sub">
            <i className="fas fa-tag mr-2"></i>版本 (Version)
          </div>
          <span className="font-bold text-success">{version}</span>
        </div>

        {/* 6. CPU */}
        <div className="glass-panel p-3 sm:p-4 rounded-2xl">
          <div className="flex items-center justify-between mb-1">
            <div className="font-bold text-text-sub">
              <i className="fas fa-microchip mr-2"></i>處理器
            </div>
            <span className="font-bold text-text-main">{cpuLoad}</span>
          </div>
          <div className="progress-bar mt-2">
            <div className="h-full bg-success rounded transition-all duration-500" style={{ width: cpuLoad === '...' ? '0%' : cpuLoad }}></div>
          </div>
        </div>

        {/* 7. 記憶體 */}
        <div className="glass-panel p-3 sm:p-4 rounded-2xl">
          <div className="flex items-center justify-between mb-1">
            <div className="font-bold text-text-sub">
              <i className="fas fa-memory mr-2"></i>記憶體
            </div>
            <span className="font-bold">{ramPercent}%</span>
          </div>
          <div className="flex justify-between text-xs text-text-sub mb-1">
            <span>Usage</span>
            <span>{ramUsed} / {ramTotal}</span>
          </div>
          <div className="progress-bar">
            <div className="h-full bg-btn-blue rounded transition-all duration-500" style={{ width: `${ramPercent}%` }}></div>
          </div>
        </div>

        {/* 8. 磁碟 */}
        <div className="glass-panel p-3 sm:p-4 rounded-2xl">
          <div className="flex items-center justify-between mb-1">
            <div className="font-bold text-text-sub">
              <i className="fas fa-hdd mr-2"></i>Disk (Root)
            </div>
            <span className="font-bold">{diskPercent}%</span>
          </div>
          <div className="flex justify-between text-xs text-text-sub mb-1">
            <span>Usage</span>
            <span>{diskUsed} / {diskTotal}</span>
          </div>
          <div className="progress-bar">
            <div className="h-full bg-btn-orange rounded transition-all duration-500" style={{ width: `${diskPercent}%` }}></div>
          </div>
        </div>

        {/* 9. 網路 */}
        <div className="glass-panel p-3 sm:p-4 rounded-2xl flex items-center justify-between">
          <div className="font-bold text-text-sub">
            <i className="fas fa-network-wired mr-2"></i>Network
          </div>
          <div className="text-xs text-white/80">
            <span className="ml-2"><i className="fas fa-arrow-down text-success"></i> {netRx}</span>
            <span className="ml-3"><i className="fas fa-arrow-up text-btn-blue"></i> {netTx}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
