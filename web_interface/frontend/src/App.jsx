// App.jsx — 主入口 (還原舊版頂部導航 + 居中單欄佈局)
import { useState, useEffect } from 'react';
import TopNav from './components/TopNav';
import Dashboard from './components/Dashboard';
import LiveConsole from './components/LiveConsole';
import ConsolePage from './components/ConsolePage';
import PlayersPage from './components/PlayersPage';
import FilesPage from './components/FilesPage';
import SettingsPage from './components/SettingsPage';
import { initApi, fetchStatus, sendPowerAction, sendCommandToConsole, fetchInstances, setCurrentInstance } from './utils/api';
import { useSmartSocket } from './hooks/useSmartSocket';

function App() {
  // 目前選中的 Tab
  const [activeTab, setActiveTab] = useState('dashboard');

  // 實例列表狀態
  const [instances, setInstances] = useState([]);
  const [currentInstance, setLocalCurrentInstance] = useState('main');

  // === Dashboard 狀態 ===
  // 透過 WebSocket 取得最新的 log 陣列，不再寫死假資料
  const [logs, setLogs] = useState([]);
  const [cpuLoad, setCpuLoad] = useState('...');
  const [ramPercent, setRamPercent] = useState(0);
  const [ramUsed, setRamUsed] = useState('...');
  const [ramTotal, setRamTotal] = useState('...');
  const [diskPercent, setDiskPercent] = useState(0);
  const [diskUsed, setDiskUsed] = useState('...');
  const [diskTotal, setDiskTotal] = useState('...');
  const [netRx, setNetRx] = useState('...');
  const [netTx, setNetTx] = useState('...');
  const [serverStatus, setServerStatus] = useState('離線');
  const [isOnline, setIsOnline] = useState(false);
  const [activePlayers, setActivePlayers] = useState(0);
  const [maxPlayers, setMaxPlayers] = useState(0);
  const [version, setVersion] = useState('Loading...');
  const [commandInput, setCommandInput] = useState('');
  const [apiReady, setApiReady] = useState(false);
  const [publicIp, setPublicIp] = useState(window.location.hostname);

  // === 智慧型連線 (Smart Connection) ===
  const { isConnected, serverState, logs: wsLogs, sendCommand } = useSmartSocket();

  // 初始化 API 與拉取實例清單
  useEffect(() => {
    const setup = async () => {
      await initApi();
      try {
        const res = await fetchInstances();
        if (res.instances) {
          setInstances(res.instances);
        }
      } catch (e) {
        console.warn('Failed to fetch instances:', e);
      }
      setApiReady(true);
    };
    setup();
  }, []);

  // 網頁首次載入（或 API 就緒）時立刻拉取一次狀態，避免等候 WebSocket 第一筆推播的空窗期
  useEffect(() => {
    if (!apiReady) return;
    const loadInitialStatus = async () => {
      try {
        const data = await fetchStatus();
        if (data && data.status === 'success') {
          // isOnline = VM2 虛擬機是否上線 (綠紅燈)
          setIsOnline(data.vm2_online);
          // serverStatus = 遊戲伺服器程式的狀態文字
          const gameOnline = data.server_status === 'online';
          setServerStatus(
            gameOnline ? '線上 (Online)' :
              data.vm2_online ? '待機中 (Standby)' : '離線 (Offline)'
          );
          if (data.stats) {
            setCpuLoad(data.stats.cpu || '...');
            setRamPercent(Math.round(data.stats.mem || 0));
          }
          if (data.public_ip) {
            setPublicIp(data.public_ip);
          }
        }
      } catch (e) {
        console.warn('Initial status fetch failed:', e);
      }
    };
    loadInitialStatus();
  }, [apiReady, currentInstance]);

  // 監聽 WebSocket 回傳的伺服器狀態與效能數據
  useEffect(() => {
    if (serverState) {
      const online = serverState.status === 'online';
      setIsOnline(online);
      setServerStatus(
        online ? '線上 (Online)' :
          serverState.status === 'starting' ? '啟動中...' : '離線 (Offline)'
      );

      const stats = serverState.system;
      if (stats) {
        setCpuLoad(stats.cpu_percent || '...');
        setRamPercent(stats.ram_percent || 0);
        setRamUsed(stats.ram_used_mb ? stats.ram_used_mb + 'MB' : '...');
        setRamTotal(stats.ram_total_mb ? stats.ram_total_mb + 'MB' : '...');
        // 如果未來 VM2 提供磁碟與網路資訊再補上
      }
      if (serverState.activePlayers !== undefined) setActivePlayers(serverState.activePlayers);
      if (serverState.maxPlayers !== undefined) setMaxPlayers(serverState.maxPlayers);
      if (serverState.version) setVersion(serverState.version);
    }
  }, [serverState]);

  // 接收 WebSocket 的 Log 串流
  useEffect(() => {
    if (wsLogs && wsLogs.length > 0) {
      // 解析原始文字並加上時間戳
      const newLogEntries = wsLogs.map(text => {
        const now = new Date();
        const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
        // 簡單判斷 Log 層級
        let level = 'INFO';
        if (text.includes('WARN')) level = 'WARN';
        if (text.includes('ERROR') || text.includes('Failed')) level = 'ERROR';
        if (text.includes('Executed:')) level = 'CMD';

        return { time: timeStr, level, message: text.trim() };
      });

      // 合併並保留最後 200 筆避免記憶體溢出
      setLogs(prev => {
        const combined = [...prev, ...newLogEntries];
        return combined.slice(-200);
      });
    }
  }, [wsLogs]);

  // 切換實例
  const handleInstanceChange = (uuid) => {
    setCurrentInstance(uuid);
    setLocalCurrentInstance(uuid);
    setServerStatus('切換中...');
    setIsOnline(false);
    setLogs([]);
    setCpuLoad('...');
    setRamPercent(0);
    // 重設其他狀態...
  };

  // 電源控制
  const handleStart = async () => {
    setServerStatus('啟動中...');
    try { await sendPowerAction('start'); } catch (e) { console.error(e); setServerStatus('離線 (Offline)'); }
  };
  const handleStop = async () => {
    setServerStatus('離線 (Offline)');
    try { await sendPowerAction('stop'); } catch (e) { console.error(e); setServerStatus('線上 (Online)'); }
  };
  const handleRestart = async () => {
    setServerStatus('重啟中...');
    try { await sendPowerAction('restart'); } catch (e) { console.error(e); }
  };

  // 發送指令
  const handleSendCommand = async () => {
    if (!commandInput.trim()) return;
    const cmd = commandInput;
    setCommandInput('');

    // 優先使用 WebSocket 發送，若連線不通才用 HTTP (可選，這裡簡化處理)
    if (isConnected) {
      sendCommand(cmd);
    } else {
      // fallback to HTTP
      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
      setLogs([...logs, { time: timeStr, level: 'CMD', message: cmd }]);
      try { await sendCommandToConsole(cmd); } catch (e) {
        setLogs(prev => [...prev, { time: timeStr, level: 'ERROR', message: 'Failed to send command' }]);
      }
    }
  };

  // 根據 Tab 渲染內容
  const renderContent = () => {
    switch (activeTab) {
      case 'console': return <ConsolePage />;
      case 'players': return <PlayersPage />;
      case 'files': return <FilesPage />;
      case 'settings': return <SettingsPage />;
      case 'dashboard':
      default:
        return (
          <>
            <Dashboard
              serverStatus={serverStatus}
              isOnline={isOnline}
              activePlayers={activePlayers}
              maxPlayers={maxPlayers}
              version={version}
              cpuLoad={cpuLoad}
              ramPercent={ramPercent}
              ramUsed={ramUsed}
              ramTotal={ramTotal}
              diskPercent={diskPercent}
              diskUsed={diskUsed}
              diskTotal={diskTotal}
              netRx={netRx}
              netTx={netTx}
              onStart={handleStart}
              onStop={handleStop}
              onRestart={handleRestart}
              publicIp={publicIp}
            />
            <LiveConsole
              logs={logs}
              commandInput={commandInput}
              wsConnected={isConnected}
              setCommandInput={setCommandInput}
              onSendCommand={handleSendCommand}
            />
          </>
        );
    }
  };

  return (
    <div className="min-h-screen p-4 md:p-8 flex justify-center items-start overflow-y-auto custom-scrollbar pt-6 lg:pt-8 text-white font-display antialiased">
      {/* 頂部導航 (固定) */}
      <TopNav
        activeTab={activeTab}
        onTabChange={setActiveTab}
        isOnline={isOnline}
        wsConnected={isConnected}
        instances={instances}
        currentInstance={currentInstance}
        onInstanceChange={handleInstanceChange}
      />

      {/* 主內容區 (居中單欄) */}
      <div className="max-w-7xl w-full flex flex-col gap-6 pt-[120px]">
        <main className="flex-1 flex flex-col gap-4 overflow-visible pb-20 w-full">
          {renderContent()}
        </main>
      </div>
      {/* 移除月亮主題浮動按鈕 */}
    </div>
  );
}

export default App;
