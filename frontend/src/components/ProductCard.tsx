import type { Product } from '../types';
import { ExternalLink } from 'lucide-react';

interface ProductCardProps {
    product: Product;
}

export function ProductCard({ product }: ProductCardProps) {
    const imageUrl = product.image_url || product.image;
    const productUrl = product.product_url || product.url;
    const matchPercent = product.score ? Math.round(product.score * 100) : null;

    return (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
            <div className="aspect-square overflow-hidden bg-gray-100 relative">
                {imageUrl ? (
                    <img
                        src={imageUrl}
                        alt={product.name}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                            e.currentTarget.style.display = 'none';
                        }}
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-400 text-4xl">
                        📦
                    </div>
                )}
                {matchPercent && (
                    <span className="absolute top-2 right-2 bg-blue-600 text-white text-xs font-semibold px-2 py-1 rounded-full">
                        {matchPercent}%
                    </span>
                )}
            </div>
            <div className="p-4">
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
