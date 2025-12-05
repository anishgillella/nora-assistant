import { useState, useEffect } from 'react';
import type { Product } from '../types';
import { dataApi, type DataResponse } from '../services/api';
import { Search, ExternalLink } from 'lucide-react';

export function DataExplorer() {
    const [activeTab, setActiveTab] = useState<'history' | 'products'>('history');
    const [searchQuery, setSearchQuery] = useState('');
    const [browsingData, setBrowsingData] = useState<DataResponse | null>(null);
    const [productsData, setProductsData] = useState<DataResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadData();
    }, [activeTab]);

    const loadData = async () => {
        setLoading(true);
        try {
            if (activeTab === 'history') {
                const data = await dataApi.getBrowsing(100, 0);
                setBrowsingData(data);
            } else {
                const data = await dataApi.getProducts(100, 0);
                setProductsData(data);
            }
        } catch (error) {
            console.error('Failed to load data:', error);
        } finally {
            setLoading(false);
        }
    };

    const browsingItems = browsingData?.data || [];
    const products = productsData?.data || [];

    const filteredHistory = browsingItems.filter((item: any) => {
        const title = item.title || item.product?.name || '';
        const url = item.url || '';
        return title.toLowerCase().includes(searchQuery.toLowerCase()) ||
            url.toLowerCase().includes(searchQuery.toLowerCase());
    });

    const filteredProducts = products.filter((product: any) =>
        (product.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (product.category || '').toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="flex flex-col h-full bg-gray-50">
            {/* Header */}
            <div className="bg-white border-b border-gray-200 px-6 py-4">
                <h1 className="text-xl font-semibold text-gray-900 mb-4">Data Explorer</h1>

                {/* Tabs */}
                <div className="flex gap-2 mb-4">
                    <button
                        onClick={() => setActiveTab('history')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === 'history'
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                    >
                        Browsing History ({browsingData?.count || 0})
                    </button>
                    <button
                        onClick={() => setActiveTab('products')}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === 'products'
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                    >
                        Product Catalog ({productsData?.count || 0})
                    </button>
                </div>

                {/* Search */}
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder={`Search ${activeTab === 'history' ? 'history' : 'products'}...`}
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
                {loading ? (
                    <div className="flex items-center justify-center h-40 text-gray-500">
                        Loading...
                    </div>
                ) : activeTab === 'history' ? (
                    <div className="space-y-3">
                        {filteredHistory.length === 0 ? (
                            <p className="text-gray-500 text-center py-8">No browsing history found</p>
                        ) : (
                            filteredHistory.map((item: any, idx: number) => (
                                <div
                                    key={item.id || idx}
                                    className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-sm transition-shadow"
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="flex-1 min-w-0">
                                            <h3 className="font-medium text-gray-900 truncate mb-1">
                                                {item.product?.name || item.title || 'Unknown'}
                                            </h3>
                                            {item.product?.brand && (
                                                <p className="text-sm text-gray-600 mb-1">{item.product.brand}</p>
                                            )}
                                            <p className="text-sm text-gray-500 truncate mb-2">{item.url}</p>
                                            <div className="flex items-center gap-4 text-xs text-gray-500">
                                                {item.product?.price && (
                                                    <span className="font-semibold text-gray-900">
                                                        ${item.product.price}
                                                    </span>
                                                )}
                                                {item.product?.category && (
                                                    <span className="bg-gray-100 px-2 py-0.5 rounded">
                                                        {item.product.category}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        {item.url && (
                                            <a
                                                href={item.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="flex-shrink-0 text-blue-600 hover:text-blue-700"
                                            >
                                                <ExternalLink className="w-4 h-4" />
                                            </a>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {filteredProducts.length === 0 ? (
                            <p className="text-gray-500 text-center py-8 col-span-full">No products found</p>
                        ) : (
                            filteredProducts.map((product: any, idx: number) => (
                                <div
                                    key={product.id || idx}
                                    className="bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-sm transition-shadow"
                                >
                                    <div className="aspect-video overflow-hidden bg-gray-100">
                                        {product.image_url ? (
                                            <img
                                                src={product.image_url}
                                                alt={product.name}
                                                className="w-full h-full object-cover"
                                                onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                            />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center text-gray-400 text-2xl">
                                                📦
                                            </div>
                                        )}
                                    </div>
                                    <div className="p-4">
                                        <div className="flex items-start justify-between gap-2 mb-2">
                                            <h3 className="font-semibold text-gray-900 text-sm line-clamp-2">
                                                {product.name}
                                            </h3>
                                            <span className="text-lg font-bold text-gray-900 whitespace-nowrap">
                                                ${product.price}
                                            </span>
                                        </div>
                                        {product.brand && (
                                            <p className="text-xs text-gray-500 mb-1">{product.brand}</p>
                                        )}
                                        {product.category && (
                                            <span className="inline-block text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded mb-2">
                                                {product.category}
                                            </span>
                                        )}
                                        {product.description && (
                                            <p className="text-sm text-gray-600 line-clamp-2">
                                                {product.description}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="bg-white border-t border-gray-200 px-6 py-3 text-xs text-gray-500 flex justify-between">
                <span>
                    Showing {activeTab === 'history' ? filteredHistory.length : filteredProducts.length} items
                </span>
                <span>
                    Last updated: {new Date().toLocaleTimeString()}
                </span>
            </div>
        </div>
    );
}
