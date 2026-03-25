// GameRulesPage.jsx - 遊戲規則編輯器頁面
import React, { useState, useEffect, useCallback } from 'react';
import { fetchGameRules, updateGameRule } from '../utils/api';
import { debounce } from 'lodash';

// 可複用的 Switch 元件
const Switch = ({ checked, onChange }) => {
    return (
        <label className="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" checked={checked} onChange={onChange} className="sr-only peer" />
            <div className="w-11 h-6 bg-gray-600 rounded-full peer peer-focus:ring-2 peer-focus:ring-blue-500/50  peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-500"></div>
        </label>
    );
};

const GameRuleCard = ({ rule, onUpdate }) => {
    const [currentValue, setCurrentValue] = useState(rule.value);
    const [saveStatus, setSaveStatus] = useState(false);

    const debouncedUpdate = useCallback(debounce((name, value) => {
        updateGameRule(name, value)
            .then(() => {
                setSaveStatus(true);
                setTimeout(() => setSaveStatus(false), 2000);
            })
            .catch(err => console.error("Failed to update gamerule", err));
    }, 500), []);

    const handleChange = (e) => {
        const newValue = rule.type === 'boolean' ? e.target.checked.toString() : e.target.value;
        setCurrentValue(newValue);
        debouncedUpdate(rule.name, newValue);
    };

    return (
        <div className="bg-black/20 p-4 rounded-lg flex items-center justify-between">
            <div>
                <p className="font-mono text-white/90">{rule.name}</p>
                {/* Could add descriptions here later */}
            </div>
            <div className="flex items-center gap-3">
                {saveStatus && <span className="text-xs text-green-400 transition-opacity">已套用</span>}
                {rule.type === 'boolean' ? (
                    <Switch checked={currentValue === 'true'} onChange={handleChange} />
                ) : (
                    <input
                        type="number"
                        value={currentValue}
                        onChange={handleChange}
                        className="w-24 bg-black/30 border border-white/20 rounded-md p-1.5 text-center"
                    />
                )}
            </div>
        </div>
    );
};


export default function GameRulesPage() {
    const [gamerules, setGamerules] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadGameRules = async () => {
            setLoading(true);
            try {
                const rules = await fetchGameRules();
                setGamerules(rules);
            } catch (error) {
                console.error("Failed to fetch gamerules", error);
            } finally {
                setLoading(false);
            }
        };
        loadGameRules();
    }, []);

    return (
        <div>
            <h2 className="text-2xl font-bold mb-4 text-white">遊戲規則</h2>
            <div className="glass-panel p-6 rounded-2xl">
                 <p className="text-sm text-white/60 mb-6">
                    此處的變更將會<strong className="text-amber-300">立即生效</strong>至伺服器，無需重啟。
                </p>
                {loading ? (
                    <div className="text-center text-gray-400"><i className="fas fa-spinner fa-spin mr-2"></i>正在從伺服器讀取規則...</div>
                ) : (
                    <div className="options-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '15px' }}>
                        {gamerules.map(rule => (
                            <GameRuleCard key={rule.name} rule={rule} onUpdate={() => {}} />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
