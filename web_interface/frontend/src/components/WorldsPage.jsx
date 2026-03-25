// WorldsPage.jsx - 世界管理頁面
import React, { useState, useEffect, useRef } from 'react';
import { fetchWorlds, switchWorld, deleteWorld, downloadWorld, uploadWorld } from '../utils/api';

export default function WorldsPage() {
    const [worlds, setWorlds] = useState([]);
    const [currentWorld, setCurrentWorld] = useState('');
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(null); // 'switch', 'delete', etc.
    const [uploadProgress, setUploadProgress] = useState(0);
    const fileInputRef = useRef(null);

    const loadWorlds = async () => {
        setLoading(true);
        try {
            const data = await fetchWorlds();
            setWorlds(data.worlds || []);
            setCurrentWorld(data.current_world || '');
        } catch (error) {
            console.error("Failed to fetch worlds:", error);
            // 在此處添加錯誤通知
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadWorlds();
    }, []);

    const handleSwitch = async (worldName) => {
        if (worldName === currentWorld) return;
        if (!window.confirm(`確定要啟用世界 "${worldName}" 嗎？伺服器將會重新啟動。`)) return;
        setActionLoading(`switch-${worldName}`);
        try {
            await switchWorld(worldName);
            alert('世界切換成功，伺服器正在重啟。');
            loadWorlds(); // 重新載入以更新狀態
        } catch (error) {
            console.error("Failed to switch world:", error);
            alert('切換世界失敗！');
        } finally {
            setActionLoading(null);
        }
    };

    const handleDelete = async (worldName) => {
        if (worldName === currentWorld) {
            alert('無法刪除正在使用的世界！');
            return;
        }
        if (!window.confirm(`【警告】即將永久刪除世界檔案 "${worldName}"！此操作無法復原，確定嗎？`)) return;
        setActionLoading(`delete-${worldName}`);
        try {
            await deleteWorld(worldName);
            alert(`世界 "${worldName}" 已被刪除。`);
            loadWorlds();
        } catch (error) {
            console.error("Failed to delete world:", error);
            alert('刪除世界失敗！');
        } finally {
            setActionLoading(null);
        }
    };
    
    const handleDownload = () => {
        if (!window.confirm('即將開始下載目前啟用的世界備份，檔案可能很大，確定要繼續嗎？')) return;
        downloadWorld();
    };

    const handleUploadTrigger = () => {
        fileInputRef.current.click();
    };

    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        if (!window.confirm(`確定要上傳 "${file.name}" 並覆寫目前的世界嗎？這個操作會導致伺服器重啟。`)) return;

        setActionLoading('upload');
        setUploadProgress(0);
        try {
            await uploadWorld(file, (progress) => {
                setUploadProgress(progress);
            });
            alert('上傳成功！伺服器正在重啟並載入新世界。');
            loadWorlds();
        } catch (error) {
            console.error('Upload failed:', error);
            alert('上傳失敗！');
        } finally {
            setActionLoading(null);
            setUploadProgress(0);
            fileInputRef.current.value = null; // Reset file input
        }
    };


    const renderWorldList = () => {
        if (loading) {
            return <div className="text-center text-gray-400">正在載入世界列表...</div>;
        }
        if (worlds.length === 0) {
            return <div className="text-center text-gray-400">找不到任何世界。</div>;
        }
        return worlds.map(world => (
            <div key={world.name} className="flex items-center justify-between p-3 bg-black/20 rounded-lg">
                <div className="flex items-center gap-3">
                    <span className={`material-symbols-outlined ${world.name === currentWorld ? 'text-green-400' : 'text-gray-400'}`}>
                        {world.name === currentWorld ? 'check_circle' : 'public'}
                    </span>
                    <span className="font-medium">{world.name}</span>
                </div>
                <div className="flex items-center gap-2">
                    {world.name === currentWorld ? (
                        <span className="px-3 py-1 text-xs font-bold text-green-300 bg-green-500/20 rounded-full">已啟用</span>
                    ) : (
                        <button
                            onClick={() => handleSwitch(world.name)}
                            disabled={actionLoading}
                            className="px-3 py-1 text-xs text-white bg-blue-500/50 hover:bg-blue-500/80 rounded transition-colors disabled:opacity-50">
                            {actionLoading === `switch-${world.name}` ? '啟用中...' : '啟用'}
                        </button>
                    )}
                    <button
                        onClick={() => handleDelete(world.name)}
                        disabled={actionLoading || world.name === currentWorld}
                        className="px-3 py-1 text-xs text-white bg-red-500/50 hover:bg-red-500/80 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                        {actionLoading === `delete-${world.name}` ? '刪除中...' : '刪除'}
                    </button>
                </div>
            </div>
        ));
    };

    return (
        <div>
            <input type="file" accept=".zip,.mcworld" ref={fileInputRef} onChange={handleFileUpload} style={{ display: 'none' }} />
            <h2 className="text-2xl font-bold mb-4 text-white">世界管理</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Left Card: World List */}
                <div className="md:col-span-2 glass-panel p-6 rounded-2xl">
                    <h3 className="text-lg font-bold mb-4 text-white/90">可用世界</h3>
                    <div className="space-y-3">
                        {renderWorldList()}
                    </div>
                </div>

                {/* Right Card: Actions */}
                <div className="glass-panel p-6 rounded-2xl space-y-4">
                     <h3 className="text-lg font-bold text-white/90">世界操作</h3>
                    {/* Download */}
                    <div className="bg-black/20 p-4 rounded-lg flex justify-between items-center">
                        <div>
                            <h4 className="font-bold text-blue-300">下載地圖</h4>
                            <p className="text-xs text-white/60 mt-1">將目前啟用的世界打包下載</p>
                        </div>
                        <button onClick={handleDownload} disabled={actionLoading} className="btn-aternos btn-blue disabled:opacity-50">
                            <i className="fas fa-download"></i>
                        </button>
                    </div>
                    {/* Upload */}
                    <div className="bg-black/20 p-4 rounded-lg">
                        <div className="flex justify-between items-center">
                             <div>
                                <h4 className="font-bold text-orange-300">上傳地圖</h4>
                                <p className="text-xs text-white/60 mt-1">上傳 .zip 覆蓋現有世界</p>
                            </div>
                            <button onClick={handleUploadTrigger} disabled={actionLoading} className="btn-aternos btn-orange disabled:opacity-50">
                                 {actionLoading === 'upload' ? <i className="fas fa-spinner fa-spin"></i> : <i className="fas fa-upload"></i>}
                            </button>
                        </div>
                        {actionLoading === 'upload' && (
                            <div className="mt-3">
                                <div className="w-full bg-gray-700 rounded-full h-2.5">
                                    <div className="bg-orange-400 h-2.5 rounded-full" style={{ width: `${uploadProgress}%` }}></div>
                                </div>
                                <p className="text-xs text-center text-orange-300 mt-1">{Math.round(uploadProgress)}%</p>
                            </div>
                        )}
                    </div>
                    {/* Reset (Placeholder) */}
                    <div className="bg-black/20 p-4 rounded-lg flex justify-between items-center">
                         <div>
                            <h4 className="font-bold text-green-300">重置世界</h4>
                            <p className="text-xs text-white/60 mt-1">刪除並重新生成一個新世界</p>
                        </div>
                        <button disabled className="btn-aternos btn-green disabled:opacity-50 cursor-not-allowed">
                            <i className="fas fa-redo"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
