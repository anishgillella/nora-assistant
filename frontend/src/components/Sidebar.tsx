import { useState, useEffect } from 'react';
import type { MemoryStats } from '../types';
import { memoryApi, recommendationsApi } from '../services/api';
import { Database, RefreshCw, Download, Upload, BarChart3, Package, Sparkles } from 'lucide-react';
import { ProfileModal } from './ProfileModal';

interface SidebarProps {
    onViewChange: (view: 'chat' | 'explorer') => void;
    currentView: 'chat' | 'explorer';
}

export function Sidebar({ onViewChange, currentView }: SidebarProps) {
    const [stats, setStats] = useState<MemoryStats | null>(null);
    const [isImporting, setIsImporting] = useState(false);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [isProfileOpen, setIsProfileOpen] = useState(false);

    useEffect(() => {
        loadStats();
    }, []);

    const loadStats = async () => {
        try {
            const data = await memoryApi.getStats();
            setStats(data);
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    };

    const handleImport = async () => {
        setIsImporting(true);
        try {
            await memoryApi.ingest({ days_back: 30, max_urls: 100, ecommerce_only: true });
            await loadStats();
        } catch (error) {
            console.error('Import failed:', error);
        } finally {
            setIsImporting(false);
        }
    };

    const handleRefresh = async () => {
        setIsRefreshing(true);
        try {
            await recommendationsApi.refresh();
            await loadStats();
        } catch (error) {
            console.error('Refresh failed:', error);
        } finally {
            setIsRefreshing(false);
        }
    };

    const handleExport = () => {
        window.open('http://localhost:8000/api/data/export/browsing', '_blank');
    };

    return (
        <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
            {/* Header */}
            <div className="p-6 border-b border-gray-200">
                <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                        <span className="text-xl">🛍️</span>
                    </div>
                    <div>
                        <h1 className="text-xl font-semibold text-gray-900">Nora</h1>
                        <p className="text-xs text-gray-500">AI Shopping Assistant</p>
                    </div>
                </div>

                <button
                    onClick={() => setIsProfileOpen(true)}
                    className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all shadow-sm"
                >
                    <Sparkles className="w-4 h-4" />
                    <span className="text-sm font-medium">Personalize Experience</span>
                </button>

                <h2 className="text-sm font-semibold text-gray-900 mb-3 mt-6">Memory Stats</h2>
                <div className="space-y-2">
                    <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
                        <Database className="w-5 h-5 text-blue-600" />
                        <div className="flex-1">
                            <p className="text-xs text-gray-600">Browsing Items</p>
                            <p className="text-lg font-semibold text-gray-900">{stats?.browsing_count || 0}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3 p-3 bg-purple-50 rounded-lg">
                        <Package className="w-5 h-5 text-purple-600" />
                        <div className="flex-1">
                            <p className="text-xs text-gray-600">Products</p>
                            <p className="text-lg font-semibold text-gray-900">{stats?.products_count || 0}</p>
                        </div>
                    </div>
                </div>
            </div>

            <ProfileModal isOpen={isProfileOpen} onClose={() => setIsProfileOpen(false)} />

            {/* Data Management */}
            <div className="p-6 border-b border-gray-200">
                <h2 className="text-sm font-semibold text-gray-900 mb-3">Data Management</h2>
                <div className="space-y-2">
                    <button
                        onClick={handleImport}
                        disabled={isImporting}
                        className="w-full flex items-center gap-3 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                    >
                        <Upload className="w-4 h-4" />
                        <span className="text-sm font-medium">
                            {isImporting ? 'Importing...' : 'Import History'}
                        </span>
                    </button>
                    <button
                        onClick={handleRefresh}
                        disabled={isRefreshing}
                        className="w-full flex items-center gap-3 px-4 py-3 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
                    >
                        <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                        <span className="text-sm font-medium">
                            {isRefreshing ? 'Refreshing...' : 'Refresh Catalog'}
                        </span>
                    </button>
                    <button
                        onClick={handleExport}
                        className="w-full flex items-center gap-3 px-4 py-3 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                        <Download className="w-4 h-4" />
                        <span className="text-sm font-medium">Export Data</span>
                    </button>
                </div>
            </div>

            {/* Views */}
            <div className="p-6">
                <h2 className="text-sm font-semibold text-gray-900 mb-3">Views</h2>
                <div className="space-y-2">
                    <button
                        onClick={() => onViewChange('chat')}
                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${currentView === 'chat'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                            }`}
                    >
                        <BarChart3 className="w-4 h-4" />
                        <span className="text-sm font-medium">Chat Assistant</span>
                    </button>
                    <button
                        onClick={() => onViewChange('explorer')}
                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${currentView === 'explorer'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                            }`}
                    >
                        <Database className="w-4 h-4" />
                        <span className="text-sm font-medium">Data Explorer</span>
                    </button>
                </div>
            </div>
        </div>
    );
}
