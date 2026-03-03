import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import LiveConsole from './components/LiveConsole';

function App() {
  const [logs, setLogs] = useState([
    { time: '14:20:01', level: 'INFO', message: 'Starting minecraft server version 1.20.71' },
    { time: '14:20:02', level: 'INFO', message: 'Loading properties' },
    { time: '14:20:05', level: 'INFO', message: 'Preparing level "world"' },
    { time: '14:20:08', level: 'WARN', message: "Can't keep up! Is the server overloaded?" },
    { time: '14:20:15', level: 'INFO', message: 'Player joined the game' },
    { time: '14:20:22', level: 'Chat', message: '<span class="text-white font-bold">&lt;Admin&gt;</span> The cherry blossoms are blooming! 🌸' },
    { time: '14:21:05', level: 'INFO', message: "Saving chunks for level 'ServerLevel'..." }
  ]);
  const [cpuUsage, setCpuUsage] = useState(45);
  const [ramUsage, setRamUsage] = useState(72);
  const [serverStatus, setServerStatus] = useState('Online');
  const [activePlayers, setActivePlayers] = useState(12);
  const [maxPlayers, setMaxPlayers] = useState(50);
  const [commandInput, setCommandInput] = useState('');

  const handleStart = () => {
    console.log("Starting server...");
    setServerStatus('Starting...');
    // TODO: Connect to explicit API call
  };

  const handleStop = () => {
    console.log("Stopping server...");
    setServerStatus('Offline');
    // TODO: Connect to explicit API call
  };

  const handleSendCommand = () => {
    if (!commandInput.trim()) return;
    console.log("Sending command:", commandInput);

    // Optimistic UI update
    const now = new Date();
    const timeStr = \`\${String(now.getHours()).padStart(2, '0')}:\${String(now.getMinutes()).padStart(2, '0')}:\${String(now.getSeconds()).padStart(2, '0')}\`;
    setLogs([...logs, { time: timeStr, level: 'CMD', message: commandInput }]);
    
    setCommandInput('');
    // TODO: Connect to explicit API call
  };

  return (
    <div className="font-display text-slate-100 antialiased h-screen overflow-hidden selection:bg-primary selection:text-white relative">
      {/* Background Image Layer */}
      <div className="fixed inset-0 z-0 bg-cherry-blossom bg-cover bg-center">
        <div className="absolute inset-0 bg-[#120810]/70"></div>
      </div>

      {/* Main Layout */}
      <div className="relative z-10 flex flex-col lg:flex-row h-full w-full p-4 gap-4">
        <Sidebar />

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col gap-4 overflow-hidden">
          <Dashboard 
            serverStatus={serverStatus}
            cpuUsage={cpuUsage}
            ramUsage={ramUsage}
            activePlayers={activePlayers}
            maxPlayers={maxPlayers}
            onStart={handleStart}
            onStop={handleStop}
          />

          <LiveConsole 
            logs={logs}
            commandInput={commandInput}
            setCommandInput={setCommandInput}
            onSendCommand={handleSendCommand}
          />
        </main>
      </div>
    </div>
  );
}

export default App;
