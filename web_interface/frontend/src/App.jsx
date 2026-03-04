// App.jsx — 主入口 (還原舊版頂部導航 + 居中單欄佈局)
import { useState, useEffect } from 'react';
import TopNav from './components/TopNav';
import Dashboard from './components/Dashboard';
import LiveConsole from './components/LiveConsole';
import ConsolePage from './components/ConsolePage';
import PlayersPage from './components/PlayersPage';
import FilesPage from './components/FilesPage';
import SettingsPage from './components/SettingsPage';
import { initApi, fetchStatus, sendPowerAction, sendCommandToConsole } from './utils/api';

function App() {
  // 目前選中的 Tab
  const [activeTab, setActiveTab] = useState('dashboard');

  // === Dashboard 狀態 ===
  const [logs, setLogs] = useState([
    { time: '14:20:01', level: 'INFO', message: 'Starting minecraft server version 1.20.71' },
    { time: '14:20:02', level: 'INFO', message: 'Loading properties' },
    { time: '14:20:05', level: 'INFO', message: 'Preparing level "world"' },
    { time: '14:20:08', level: 'WARN', message: "Can't keep up! Is the server overloaded?" },
    { time: '14:20:15', level: 'INFO', message: 'Player joined the game' },
  ]);
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

  // 初始化 API
  useEffect(() => {
    const setup = async () => {
      await initApi();
      setApiReady(true);
    };
    setup();
  }, []);

  // 每 5 秒拉取伺服器狀態
  useEffect(() => {
    if (!apiReady) return;
    const pullData = async () => {
      try {
        const data = await fetchStatus();
        if (data.status === 'success') {
          const online = data.server_status === 'online';
          setIsOnline(online);
          setServerStatus(
            online ? '線上 (Online)' :
              data.server_status === 'starting' ? '啟動中...' : '離線 (Offline)'
          );
          if (data.stats) {
            setCpuLoad(data.stats.cpu_load || '...');
            setRamPercent(Math.round(data.stats.mem || 0));
            setRamUsed(data.stats.ram_used || '...');
            setRamTotal(data.stats.ram_total || '...');
            setDiskPercent(Math.round(data.stats.disk_percent || 0));
            setDiskUsed(data.stats.disk_used || '...');
            setDiskTotal(data.stats.disk_total || '...');
            setNetRx(data.stats.net_rx || '...');
            setNetTx(data.stats.net_tx || '...');
          }
          if (data.players_online !== undefined) setActivePlayers(data.players_online);
          if (data.max_players !== undefined) setMaxPlayers(data.max_players);
          if (data.version) setVersion(data.version);
        }
      } catch (_) { }
    };
    pullData();
    const interval = setInterval(pullData, 5000);
    return () => clearInterval(interval);
  }, [apiReady]);

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
    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
    setLogs([...logs, { time: timeStr, level: 'CMD', message: cmd }]);
    try { await sendCommandToConsole(cmd); } catch (e) {
      setLogs(prev => [...prev, { time: timeStr, level: 'ERROR', message: 'Failed to send command' }]);
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
            />
            <LiveConsole
              logs={logs}
              commandInput={commandInput}
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
      <TopNav activeTab={activeTab} onTabChange={setActiveTab} isOnline={isOnline} />

      {/* 主內容區 (居中單欄) */}
      <div className="max-w-7xl w-full flex flex-col gap-6 pt-[120px]">
        <main className="flex-1 flex flex-col gap-4 overflow-visible pb-20 w-full">
          {renderContent()}
        </main>
      </div>

      {/* 主題切換浮動按鈕 */}
      <button className="fixed bottom-8 right-8 w-12 h-12 glass-panel flex items-center justify-center hover:scale-110 transition-transform rounded-full">
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
            strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
        </svg>
      </button>
    </div>
  );
}

export default App;
