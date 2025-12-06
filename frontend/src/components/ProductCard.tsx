import { useState } from 'react';
import type { Product } from '../types';
import { ExternalLink, Heart, DollarSign, Tag, Eye, Sparkles, Star } from 'lucide-react';

interface ProductCardProps {
    product: Product;
}

// Map reason codes to display info
const REASON_MAP: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
    brand_match: { label: "Your brand", icon: <Heart className="w-3 h-3" />, color: "bg-pink-100 text-pink-700" },
    price_fit: { label: "Great price", icon: <DollarSign className="w-3 h-3" />, color: "bg-green-100 text-green-700" },
    category_match: { label: "Your style", icon: <Tag className="w-3 h-3" />, color: "bg-purple-100 text-purple-700" },
    viewed_before: { label: "Viewed before", icon: <Eye className="w-3 h-3" />, color: "bg-blue-100 text-blue-700" },
    style_match: { label: "Style match", icon: <Sparkles className="w-3 h-3" />, color: "bg-amber-100 text-amber-700" },
    highly_rated: { label: "Popular", icon: <Star className="w-3 h-3" />, color: "bg-yellow-100 text-yellow-700" },
};

// Map categories to icons
import { Laptop, ShoppingBag, Home, Tent, Watch, Shirt, Footprints } from 'lucide-react';

const getCategoryPlaceholder = (category: string = '') => {
    const c = category.toLowerCase();
    if (c.includes('electronic') || c.includes('tech') || c.includes('appliance')) return <Laptop className="w-12 h-12 text-gray-300" />;
    if (c.includes('shoe') || c.includes('footwear')) return <Footprints className="w-12 h-12 text-gray-300" />;
    if (c.includes('cloth') || c.includes('apparel')) return <Shirt className="w-12 h-12 text-gray-300" />;
    if (c.includes('home') || c.includes('furniture')) return <Home className="w-12 h-12 text-gray-300" />;
    if (c.includes('outdoor')) return <Tent className="w-12 h-12 text-gray-300" />;
    if (c.includes('accessor')) return <Watch className="w-12 h-12 text-gray-300" />;
    return <ShoppingBag className="w-12 h-12 text-gray-300" />;
};

export function ProductCard({ product }: ProductCardProps) {
    const [imageError, setImageError] = useState(false);
    const imageUrl = product.image_url || product.image;
    const productUrl = product.product_url || product.url;
    const matchPercent = product.score ? Math.round(product.score * 100) : null;
    const reasonCodes = (product as any).reason_codes || [];

    return (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
            <div className="aspect-square overflow-hidden bg-gray-50 relative flex items-center justify-center">
                {imageUrl && !imageError ? (
                    <img
                        src={imageUrl}
                        alt={product.name}
                        className="w-full h-full object-cover"
                        onError={() => setImageError(true)}
                    />
                ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center bg-gray-50 p-4 text-center">
                        {getCategoryPlaceholder(product.category)}
                        <span className="text-xs text-gray-400 mt-2 font-medium capitalize">
                            {product.category || 'Product'}
                        </span>
                    </div>
                )}
                {matchPercent && (
                    <span className="absolute top-2 right-2 bg-blue-600 text-white text-xs font-semibold px-2 py-1 rounded-full">
                        {matchPercent}%
                    </span>
                )}
            </div>
            <div className="p-4">
                {/* Why This Product? - Personalized Reason */}
                {(product as any).reason_text && (
                    <div className="bg-blue-50 border-l-4 border-blue-500 px-3 py-2 mb-3 rounded-r">
                        <p className="text-sm text-blue-800 italic">
                            💡 {(product as any).reason_text}
                        </p>
                    </div>
                )}

                {/* Legacy reason codes fallback */}
                {!((product as any).reason_text) && reasonCodes.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2">
                        {reasonCodes.slice(0, 3).map((code: string) => {
                            const reason = REASON_MAP[code];
                            if (!reason) return null;
                            return (
                                <span
                                    key={code}
                                    className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${reason.color}`}
                                >
                                    {reason.icon}
                                    {reason.label}
                                </span>
                            );
                        })}
                    </div>
                )}

                <div className="flex items-start justify-between gap-2 mb-2">
                    <h3 className="font-semibold text-gray-900 line-clamp-2 text-sm">
                        {product.name}
                    </h3>
                    <span className="text-lg font-bold text-gray-900 whitespace-nowrap">
                        ${typeof product.price === 'number' ? product.price.toFixed(2) : product.price}
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
                    <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                        {product.description}
                    </p>
                )}
                {productUrl && (
                    <a
                        href={productUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700"
                    >
                        View Product
                        <ExternalLink className="w-4 h-4" />
                    </a>
                )}
            </div>
        </div>
    );
}
