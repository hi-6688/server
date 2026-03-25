// InstanceModal.jsx - 新增實例的彈出視窗
import React, { useState } from 'react';

export default function InstanceModal({ isOpen, onClose, onCreate }) {
    const [name, setName] = useState('');
    const [port, setPort] = useState('');
    const [channelId, setChannelId] = useState('');
    const [loading, setLoading] = useState(false);

    const handleCreate = async () => {
        if (!name || !port) {
            alert('實例名稱和 Port 不可為空！');
            return;
        }
        setLoading(true);
        try {
            await onCreate(name, port, channelId);
            onClose(); // Close modal on success
        } catch (error) {
            console.error("Failed to create instance:", error);
            alert(`建立失敗: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
            background: 'rgba(0,0,0,0.85)', zIndex: 2000,
            display: 'flex', justifyContent: 'center', alignItems: 'center'
        }}>
            <div style={{
                background: '#252830', padding: '25px', borderRadius: '8px',
                width: '400px', boxShadow: '0 4px 15px rgba(0,0,0,0.5)'
            }}>
                <h3 style={{
                    color: 'white', marginBottom: '20px', borderBottom: '1px solid #444',
                    paddingBottom: '10px', display: 'flex', alignItems: 'center', gap: '10px'
                }}>
                    <span className="material-symbols-outlined">add_circle</span>
                    新增伺服器實例
                </h3>

                <label className="text-sm text-gray-400 block mb-1">實例名稱 (Instance Name)</label>
                <input
                    id="newInstanceName"
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="例如: 生存服 (Survival)"
                    className="w-full p-2.5 mb-4 bg-[#1a1d23] border border-gray-600 text-white rounded-md"
                />

                <label className="text-sm text-gray-400 block mb-1">連接埠 (IPv4 Port)</label>
                <input
                    id="newInstancePort"
                    type="number"
                    value={port}
                    onChange={(e) => setPort(e.target.value)}
                    placeholder="例如: 19134"
                    className="w-full p-2.5 mb-2 bg-[#1a1d23] border border-gray-600 text-white rounded-md"
                />
                <div className="text-xs text-gray-500 mb-4">IPv6 將自動設為 Port + 1</div>

                <label className="text-sm text-gray-400 block mb-1">Discord 頻道 ID (選填)</label>
                <input
                    id="newInstanceChannel"
                    type="text"
                    value={channelId}
                    onChange={(e) => setChannelId(e.target.value)}
                    placeholder="例如: 123456789012345678"
                    className="w-full p-2.5 mb-6 bg-[#1a1d23] border border-gray-600 text-white rounded-md"
                />

                <div className="flex justify-end gap-3">
                    <button onClick={onClose} disabled={loading} className="px-4 py-2 bg-transparent border border-gray-600 text-gray-300 rounded-md hover:bg-gray-700 transition-colors">
                        取消
                    </button>
                    <button onClick={handleCreate} disabled={loading} className="px-4 py-2 bg-green-600 border-none text-white rounded-md hover:bg-green-700 transition-colors font-bold disabled:opacity-50">
                        {loading ? <><i className="fas fa-spinner fa-spin mr-2"></i>建立中...</> : '建立'}
                    </button>
                </div>
            </div>
        </div>
    );
}
