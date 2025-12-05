export interface BrowsingHistoryItem {
    id: string;
    url: string;
    title: string;
    timestamp: Date;
    visitCount: number;
    product?: {
        name: string;
        price: number;
        brand: string;
        category: string;
    };
}

export interface Product {
    id: string;
    name: string;
    price: number;
    image?: string;
    image_url?: string;
    url?: string;
    product_url?: string;
    category: string;
    description: string;
    brand?: string;
    score?: number;
}

export interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    products?: Product[];
    timestamp: Date;
}

export interface MemoryStats {
    total_vectors: number;
    browsing_count: number;
    products_count: number;
    last_ingest?: string;
}
