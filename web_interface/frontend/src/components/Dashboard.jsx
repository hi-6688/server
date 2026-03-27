// Dashboard.jsx — 還原舊版儀表板：狀態區 + 8 張資訊卡片 (單欄)

// 開機進度步驟定義
const BOOT_STEPS = [
  { key: 'vm_starting', label: '啟動雲端主機', icon: 'fa-cloud' },
  { key: 'agent_waiting', label: '等待代理連線', icon: 'fa-satellite-dish' },
  { key: 'server_starting', label: '啟動遊戲伺服器', icon: 'fa-gamepad' },
];

// 取得目前進度的步驟索引 (0-based, -1 代表尚未開始)
function getBootStepIndex(progress) {
  const idx = BOOT_STEPS.findIndex(s => s.key === progress);
  if (progress === 'online') return BOOT_STEPS.length; // 全部完成
  return idx;
}

export default function Dashboard({
  serverStatus, isOnline, isBooting, bootProgress, bootError,
  vm2Online, gameRunning,
  activePlayers, maxPlayers, version,
  cpuLoad, ramPercent, ramUsed, ramTotal,
  diskPercent, diskUsed, diskTotal, netRx, netTx,
  onStart, onStop, onRestart, publicIp
}) {
  const currentStep = bootProgress ? getBootStepIndex(bootProgress.progress) : -1;

  return (
    <div className="flex flex-col gap-4">
      {/* 開機失敗內嵌錯誤提示 (取代 alert) */}
      {bootError && (
        <div className="glass-panel rounded-2xl p-4 border border-red-500/30 bg-red-500/10 flex items-center gap-3 animate-pulse">
          <i className="fas fa-exclamation-triangle text-red-400 text-lg"></i>
          <div className="flex-1">
            <span className="text-red-300 font-bold text-sm">啟動異常</span>
            <p className="text-red-200/80 text-xs mt-0.5">{bootError}</p>
          </div>
          <span className="text-red-400/50 text-xs">8 秒後自動關閉</span>
        </div>
      )}

      {/* 伺服器狀態區 */}
      <div className="glass-panel p-4 sm:p-6 rounded-2xl flex flex-col gap-4">
        {/* 上排：標題 + 分層徽章 + 電源按鈕 */}
        <div className="flex flex-col sm:flex-row items-center sm:justify-between text-center sm:text-left gap-4">
          <div className="flex flex-col sm:flex-row items-center gap-3 sm:gap-4">
            <h2 className="text-lg sm:text-xl font-bold text-white whitespace-nowrap">伺服器狀態</h2>
            <div className="flex flex-wrap gap-2">
              {/* 雲端主機 (VM2) 狀態徽章 */}
              <div className="status-badge" title="GCP 雲端虛擬機狀態">
                <i className={`fas fa-cloud text-[10px] ${vm2Online ? 'text-green-400' : 'text-white/30'}`}></i>
                <div className={`status-dot ${vm2Online ? 'status-dot-online' : 'status-dot-offline'}`}></div>
                <span className="text-xs">主機 {vm2Online ? 'ON' : 'OFF'}</span>
              </div>
              {/* 遊戲伺服器狀態徽章 */}
              <div className="status-badge" title="Minecraft BDS 遊戲伺服器狀態">
                <i className={`fas fa-gamepad text-[10px] ${gameRunning ? 'text-green-400' : 'text-white/30'}`}></i>
                {isBooting ? (
                  <i className="fas fa-spinner fa-spin text-yellow-400 text-[8px]"></i>
                ) : (
                  <div className={`status-dot ${gameRunning ? 'status-dot-online' : 'status-dot-offline'}`}></div>
                )}
                <span className="text-xs">{isBooting ? serverStatus : (gameRunning ? '運行中' : '未啟動')}</span>
              </div>
              {/* 玩家人數徽章 */}
              <div className="status-badge" title="線上玩家人數">
                <i className="fas fa-users text-[10px] text-text-sub"></i>
                <span className="text-xs">{activePlayers} / {maxPlayers}</span>
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
              <button
                className={`btn-power ${isBooting ? 'opacity-50 cursor-not-allowed' : ''}`}
                onClick={isBooting ? undefined : onStart}
                disabled={isBooting}
              >
                <i className={`fas ${isBooting ? 'fa-spinner fa-spin' : 'fa-power-off'}`}></i>
                <span className="ml-2">{isBooting ? '啟動中' : '啟動'}</span>
              </button>
            )}
            <button className="btn-power btn-power-restart" onClick={onRestart} disabled={isBooting}>
              <i className="fas fa-sync-alt"></i>
              <span className="ml-2">重啟</span>
            </button>
          </div>
        </div>

        {/* 開機進度條 (僅開機時顯示) */}
        {isBooting && (
          <div className="mt-2 p-3 sm:p-4 rounded-xl bg-white/5 border border-white/10">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-bold text-yellow-400">
                <i className="fas fa-rocket mr-2"></i>開機進度
              </span>
              <span className="text-xs text-text-sub">
                {bootProgress?.message || '處理中...'}
              </span>
            </div>
            {/* 3 步驟進度指示器 */}
            <div className="flex items-center gap-0">
              {BOOT_STEPS.map((step, i) => {
                const isDone = currentStep > i;
                const isActive = currentStep === i;
                return (
                  <div key={step.key} className="flex items-center flex-1">
                    {/* 步驟圓圈 */}
                    <div className="flex flex-col items-center flex-1">
                      <div className={`
                        w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-sm
                        transition-all duration-500 border-2
                        ${isDone ? 'bg-green-500/30 border-green-400 text-green-400' :
                          isActive ? 'bg-yellow-500/20 border-yellow-400 text-yellow-400 animate-pulse' :
                          'bg-white/5 border-white/20 text-white/30'}
                      `}>
                        {isDone ? (
                          <i className="fas fa-check"></i>
                        ) : isActive ? (
                          <i className={`fas ${step.icon} fa-beat-fade`}></i>
                        ) : (
                          <i className={`fas ${step.icon}`}></i>
                        )}
                      </div>
                      <span className={`text-[10px] sm:text-xs mt-1.5 text-center leading-tight
                        ${isDone ? 'text-green-400' : isActive ? 'text-yellow-400 font-bold' : 'text-white/30'}
                      `}>
                        {step.label}
                      </span>
                    </div>
                    {/* 連接線 (最後一步不需要) */}
                    {i < BOOT_STEPS.length - 1 && (
                      <div className={`h-0.5 flex-1 mx-1 mb-5 transition-all duration-500
                        ${isDone ? 'bg-green-400' : 'bg-white/10'}
                      `}></div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
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
