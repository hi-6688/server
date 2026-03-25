import { useState, useEffect, useRef, useCallback } from 'react';

// 從網址推算 WS 伺服器位置 (現在與 API 統一使用 24445)
const getWsUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const apiKey = new URLSearchParams(window.location.search).get('key') || '';
    
    // 開發環境使用 24445，正式環境使用當前 Port (通常也是 24445)
    let port = window.location.port;
    if (port === '5173' || port === '5174' || !port) {
        port = '24445';
    }
    
    return `${protocol}//${host}:${port}/ws?key=${apiKey}`;
};

export function useSmartSocket() {
    const [isConnected, setIsConnected] = useState(false);
    const [serverState, setServerState] = useState(null);
    const [logs, setLogs] = useState([]);

    const wsRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);
    const pingIntervalRef = useRef(null);

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        console.log('[useSmartSocket] Connecting to Smart Socket...');
        const wsUrl = getWsUrl();
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('[useSmartSocket] Connected!');
            setIsConnected(true);

            // 啟動心跳包 (每 15 秒打一次 ping)
            pingIntervalRef.current = window.setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ action: 'ping' }));
                }
            }, 15000);

            // 若之前有斷線重連計時器，把它清掉
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
                reconnectTimeoutRef.current = null;
            }
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);

                if (message.type === 'server_status') {
                    setServerState(message.data);
                }
                else if (message.type === 'console_log') {
                    // 新增收到的 log
                    setLogs(prev => [...prev, message.data]);
                }
            } catch (err) {
                console.error('[useSmartSocket] Parse Error:', err);
            }
        };

        ws.onclose = () => {
            console.warn('[useSmartSocket] Disconnected. Will retry in 3 seconds...');
            setIsConnected(false);
            if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);

            // 自動重連機制
            reconnectTimeoutRef.current = setTimeout(() => {
                connect();
            }, 3000);
        };

        ws.onerror = (err) => {
            console.error('[useSmartSocket] Socket Error:', err);
            ws.close(); // 觸發 onclose 來走自動重連
        };

        wsRef.current = ws;
    }, []);

    // 掛載時啟動連線，卸載時關閉
    useEffect(() => {
        connect();

        return () => {
            if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
            if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, [connect]);

    // 提供一個發送指令的方法
    const sendCommand = useCallback((command) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                action: 'console_command',
                command: command
            }));
            return true;
        }
        return false;
    }, []);

    // 暴露介面
    return {
        isConnected,
        serverState,
        logs,
        sendCommand
    };
}
