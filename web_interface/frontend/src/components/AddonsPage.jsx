// AddonsPage.jsx - 模組管理頁面
import React, { useState, useEffect, useRef } from 'react';
import { fetchAddons, deleteAddon, uploadAddon } from '../utils/api';

const AddonCard = ({ pack, type, onDelete, actionLoading }) => (
    <div className="bg-black/20 p-4 rounded-lg flex items-center justify-between">
        <div className="flex items-center gap-4">
            <span className="material-symbols-outlined text-blue-300 text-2xl">extension</span>
            <div>
                <p className="font-bold text-white/90">{pack.name || '未知模組'}</p>
                <p className="text-xs text-white/50 font-mono">{pack.uuid}</p>
            </div>
        </div>
        <button
            onClick={() => onDelete(pack.name, type)}
            disabled={actionLoading}
            className="px-3 py-1 text-xs text-white bg-red-500/50 hover:bg-red-500/80 rounded transition-colors disabled:opacity-50"
        >
            {actionLoading === `delete-${type}-${pack.name}` ? <i className="fas fa-spinner fa-spin"></i> : '刪除'}
        </button>
    </div>
);

export default function AddonsPage() {
    const [behaviorPacks, setBehaviorPacks] = useState([]);
    const [resourcePacks, setResourcePacks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(null);
    const [uploadProgress, setUploadProgress] = useState(0);
    const fileInputRef = useRef(null);

    const loadAddons = async () => {
        setLoading(true);
        try {
            const data = await fetchAddons();
            setBehaviorPacks(data.behavior_packs || []);
            setResourcePacks(data.resource_packs || []);
        } catch (error) {
            console.error("Failed to fetch addons:", error);
            // Handle error notification
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadAddons();
    }, []);

    const handleDelete = async (addonName, addonType) => {
        if (!window.confirm(`確定要刪除 ${addonType === 'behavior_packs' ? '行為包' : '資源包'}: "${addonName}"？此操作無法復原。`)) return;
        setActionLoading(`delete-${addonType}-${addonName}`);
        try {
            await deleteAddon(addonName, addonType);
            alert('模組刪除成功！');
            loadAddons();
        } catch (error) {
            console.error('Failed to delete addon:', error);
            alert('刪除模組失敗！');
        } finally {
            setActionLoading(null);
        }
    };

    const handleUploadTrigger = () => {
        fileInputRef.current.click();
    };

    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;
        if (!window.confirm(`確定要上傳並安裝模組 "${file.name}"？`)) return;
        
        setActionLoading('upload');
        setUploadProgress(0);
        try {
            await uploadAddon(file, (progress) => {
                setUploadProgress(progress);
            });
            alert('模組安裝成功！');
            loadAddons();
        } catch (error) {
            console.error('Upload failed:', error);
            alert(`安裝失敗: ${error.message}`);
        } finally {
            setActionLoading(null);
            setUploadProgress(0);
            fileInputRef.current.value = null;
        }
    };

    const renderPackList = (packs, type) => {
        if (loading) {
            return <div className="text-center text-gray-400 p-4"><i className="fas fa-spinner fa-spin"></i> 載入中...</div>;
        }
        if (packs.length === 0) {
            return <div className="text-center text-gray-400 p-4">沒有已安裝的模組</div>;
        }
        return (
            <div className="space-y-3">
                {packs.map((pack, index) => (
                    <AddonCard key={index} pack={pack} type={type} onDelete={handleDelete} actionLoading={actionLoading} />
                ))}
            </div>
        );
    };

    return (
        <div>
            <input type="file" accept=".mcpack,.mcaddon,.zip" ref={fileInputRef} onChange={handleFileUpload} style={{ display: 'none' }} />
            <h2 className="text-2xl font-bold mb-4 text-white">模組管理</h2>

            {/* Upload Section */}
            <div className="glass-panel p-6 rounded-2xl mb-6">
                <h3 className="text-lg font-bold mb-4 text-white/90">安裝新模組</h3>
                <div className="bg-black/20 p-4 rounded-lg">
                    <div className="flex items-center gap-4">
                        <p className="text-sm text-white/70 flex-grow">支援格式： .mcpack, .mcaddon, .zip</p>
                        <button onClick={handleUploadTrigger} disabled={actionLoading === 'upload'} className="btn-aternos btn-blue disabled:opacity-50">
                            {actionLoading === 'upload' ? <i className="fas fa-spinner fa-spin"></i> : <><i className="fas fa-upload mr-2"></i>選擇檔案</>}
                        </button>
                    </div>
                    {actionLoading === 'upload' && (
                        <div className="mt-4">
                            <div className="w-full bg-gray-700 rounded-full h-2.5">
                                <div className="bg-blue-500 h-2.5 rounded-full" style={{ width: `${uploadProgress}%` }}></div>
                            </div>
                            <p className="text-xs text-center text-blue-300 mt-1">上傳中... {Math.round(uploadProgress)}%</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Lists Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="glass-panel p-6 rounded-2xl">
                    <h3 className="text-lg font-bold mb-4 text-white/90">行為包 (Behavior Packs)</h3>
                    {renderPackList(behaviorPacks, 'behavior_packs')}
                </div>
                <div className="glass-panel p-6 rounded-2xl">
                    <h3 className="text-lg font-bold mb-4 text-white/90">資源包 (Resource Packs)</h3>
                    {renderPackList(resourcePacks, 'resource_packs')}
                </div>
            </div>
        </div>
    );
}
