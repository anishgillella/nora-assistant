import { useState, useEffect } from 'react';
import { dataApi, type DataResponse } from '../services/api';
import { Search } from 'lucide-react';

export function DataExplorer() {
    const [activeTab, setActiveTab] = useState<'history' | 'products'>('history');
    const [searchQuery, setSearchQuery] = useState('');
    const [browsingData, setBrowsingData] = useState<DataResponse | null>(null);
    const [productsData, setProductsData] = useState<DataResponse | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadAllData();
    }, []);

    const loadAllData = async () => {
        setLoading(true);
        try {
            // Load both datasets on mount for accurate tab counts
            const [browsing, products] = await Promise.all([
                dataApi.getBrowsing(500, 0),
                dataApi.getProducts(500, 0)
            ]);
            setBrowsingData(browsing);
            setProductsData(products);
        } catch (error) {
            console.error('Failed to load data:', error);
        } finally {
            setLoading(false);
        }
    };

    const browsingItems = browsingData?.data || [];
    const products = productsData?.data || [];

    const filteredHistory = browsingItems.filter((item: any) => {
        const title = item.title || '';
        const url = item.url || '';
        const pName = item.product?.name || '';
        const pBrand = item.product?.brand || '';
        const pDesc = item.product?.description || '';

        const q = searchQuery.toLowerCase();

        return title.toLowerCase().includes(q) ||
            url.toLowerCase().includes(q) ||
            pName.toLowerCase().includes(q) ||
            pBrand.toLowerCase().includes(q) ||
            pDesc.toLowerCase().includes(q);
    });

    const filteredProducts = products.filter((product: any) => {
        const name = product.name || '';
        const brand = product.brand || '';
        const category = product.category || '';
        const desc = product.description || '';

        const q = searchQuery.toLowerCase();

        return name.toLowerCase().includes(q) ||
            brand.toLowerCase().includes(q) ||
            category.toLowerCase().includes(q) ||
            desc.toLowerCase().includes(q);
    });

    return (
        <div className="flex flex-col h-full bg-gray-50">
            {/* Header */}
            <div className="bg-white border-b border-gray-200 px-6 py-4">
                <h1 className="text-xl font-semibold text-gray-900 mb-4">Data Explorer</h1>

                {/* Tabs */}
                <div className="flex gap-2 mb-4">
                    <button
                        onClick={() => setActiveTab('history')}
                        className={`px - 4 py - 2 rounded - lg text - sm font - medium transition - colors ${activeTab === 'history'
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            } `}
                    >
                        Browsing History ({browsingData?.count || 0})
                    </button>
                    <button
                        onClick={() => setActiveTab('products')}
                        className={`px - 4 py - 2 rounded - lg text - sm font - medium transition - colors ${activeTab === 'products'
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            } `}
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
                ) : (
                    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Title / URL</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Brand</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Context</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Vibe</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Price</th>
                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Visit Date</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {activeTab === 'history' ? (
                                    filteredHistory.length === 0 ? (
                                        <tr><td colSpan={9} className="px-4 py-4 text-center text-gray-500">No browsing history found</td></tr>
                                    ) : (
                                        filteredHistory.map((item: any, idx: number) => {
                                            // Determine activity type and icon
                                            const activityType = item.activity_type || (item.product ? 'product' : 'content');
                                            const typeIcons: Record<string, string> = {
                                                'product': '🛒',
                                                'content': '📺',
                                                'social': '💼',
                                                'search': '🔍',
                                                'utility': '⚙️'
                                            };
                                            const typeIcon = typeIcons[activityType] || '📄';

                                            // Get unified fields (support both new and legacy format)
                                            const category = item.category || item.product?.category || '';
                                            const topics = item.topics?.join(', ') || '';
                                            const context = item.context?.join(', ') || item.product?.occasion?.join(', ') || '';
                                            const vibe = item.vibe?.join(', ') || item.product?.visual_characteristics?.join(', ') || '';
                                            const brand = item.brand || item.product?.brand || item.domain || '';
                                            const price = item.price || item.product?.price;
                                            const title = item.title || item.product?.name || 'Unknown';

                                            return (
                                                <tr key={item.id || idx} className="hover:bg-gray-50">
                                                    <td className="px-4 py-4 whitespace-nowrap text-center">
                                                        <span className="text-lg" title={activityType}>{typeIcon}</span>
                                                    </td>
                                                    <td className="px-4 py-4 text-sm text-gray-900 max-w-[180px]">
                                                        <div className="font-medium truncate">{title}</div>
                                                        <a href={item.url} target="_blank" className="text-xs text-blue-500 hover:underline truncate block" rel="noreferrer">{item.domain || item.url}</a>
                                                    </td>
                                                    <td className="px-4 py-4 text-xs text-gray-600 max-w-[280px]">
                                                        <div
                                                            className="cursor-pointer hover:text-gray-900 group"
                                                            onClick={(e) => {
                                                                const div = e.currentTarget;
                                                                div.classList.toggle('line-clamp-2');
                                                            }}
                                                            title="Click to expand/collapse"
                                                        >
                                                            <span className="line-clamp-2 group-hover:line-clamp-none">
                                                                {item.semantic_summary || item.product?.description || '-'}
                                                            </span>
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                                                        {brand || '-'}
                                                    </td>
                                                    <td className="px-4 py-4 text-sm text-gray-500">
                                                        {category && <span className="bg-gray-100 px-2 py-0.5 rounded text-xs">{category}</span>}
                                                    </td>
                                                    <td className="px-4 py-4 text-xs text-gray-500 max-w-[120px] truncate">
                                                        {context || '-'}
                                                    </td>
                                                    <td className="px-4 py-4 text-xs text-gray-500 max-w-[120px] truncate">
                                                        {vibe || '-'}
                                                    </td>
                                                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
                                                        {price ? `$${price}` : '-'}
                                                    </td>
                                                    <td className="px-4 py-4 whitespace-nowrap text-xs text-gray-400">
                                                        {item.visit_time ? new Date(item.visit_time).toLocaleDateString() : '-'}
                                                    </td>
                                                </tr>
                                            );
                                        })
                                    )
                                ) : (
                                    filteredProducts.length === 0 ? (
                                        <tr><td colSpan={9} className="px-6 py-4 text-center text-gray-500">No products found</td></tr>
                                    ) : (
                                        filteredProducts.map((product: any, idx: number) => (
                                            <tr key={product.id || idx} className="hover:bg-gray-50">
                                                <td className="px-4 py-4 whitespace-nowrap">
                                                    <div className="h-10 w-10 rounded bg-gray-100 overflow-hidden">
                                                        {product.image_url ? (
                                                            <img src={product.image_url} alt="" className="h-full w-full object-cover" />
                                                        ) : (
                                                            <div className="h-full w-full flex items-center justify-center text-lg">📦</div>
                                                        )}
                                                    </div>
                                                </td>
                                                <td className="px-4 py-4 text-sm text-gray-900 max-w-[180px]">
                                                    <div className="font-medium truncate">{product.name}</div>
                                                    <a href={product.product_url} target="_blank" className="text-xs text-blue-500 hover:underline truncate block" rel="noreferrer">{product.store_name || 'View'}</a>
                                                </td>
                                                <td className="px-4 py-4 text-xs text-gray-600 max-w-[280px]">
                                                    <div
                                                        className="cursor-pointer hover:text-gray-900 group"
                                                        onClick={(e) => {
                                                            const div = e.currentTarget;
                                                            div.classList.toggle('line-clamp-2');
                                                        }}
                                                        title="Click to expand/collapse"
                                                    >
                                                        <span className="line-clamp-2 group-hover:line-clamp-none">
                                                            {product.description || '-'}
                                                        </span>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                                                    {product.brand || '-'}
                                                </td>
                                                <td className="px-4 py-4 text-sm text-gray-500">
                                                    {product.category && <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-xs">{product.category}</span>}
                                                </td>
                                                <td className="px-4 py-4 text-xs text-gray-500 max-w-[120px] truncate">
                                                    {product.occasion?.join(', ') || '-'}
                                                </td>
                                                <td className="px-4 py-4 text-xs text-gray-500 max-w-[120px] truncate">
                                                    {product.visual_characteristics?.join(', ') || '-'}
                                                </td>
                                                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900 font-bold">
                                                    {product.price ? `$${product.price}` : '-'}
                                                </td>
                                                <td className="px-4 py-4 whitespace-nowrap text-xs text-gray-400">
                                                    {product.created_at ? new Date(product.created_at).toLocaleDateString() : 'Synced'}
                                                </td>
                                            </tr>
                                        ))
                                    )
                                )}
                            </tbody>
                        </table>
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
