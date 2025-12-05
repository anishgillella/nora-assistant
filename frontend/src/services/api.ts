const API_BASE_URL = 'http://localhost:8000/api';

export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    timestamp?: string;
}

export interface ChatResponse {
    response: string;
    query_type: string;
    sources: {
        browsing: any[];
        products: any[];
    };
}

export interface Product {
    id: string;
    name: string;
    price: number;
    brand: string;
    category: string;
    description: string;
    image_url?: string;
    product_url?: string;
    store_name?: string;
    score: number;
}

export interface MemoryStats {
    total_vectors: number;
    browsing_count: number;
    products_count: number;
    last_ingest?: string;
}

export interface Conversation {
    id: string;
    title: string;
    messages: ChatMessage[];
    created_at: string;
    updated_at: string;
}

export interface TokenStats {
    model: string;
    api_calls: number;
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    total_cost_usd: number;
}

// Chat API
export const chatApi = {
    async sendMessage(message: string, history: ChatMessage[] = []): Promise<ChatResponse> {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                conversation_history: history,
                stream: false,
            }),
        });
        if (!response.ok) throw new Error('Chat request failed');
        return response.json();
    },

    streamMessage(message: string, history: ChatMessage[] = [], onChunk: (data: any) => void): () => void {
        const controller = new AbortController();

        fetch(`${API_BASE_URL}/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                conversation_history: history,
                stream: true,
            }),
            signal: controller.signal,
        }).then(async (response) => {
            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            while (reader) {
                const { done, value } = await reader.read();
                if (done) break;

                const lines = decoder.decode(value).split('\n');
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            onChunk(data);
                        } catch (e) {
                            // Skip invalid JSON
                        }
                    }
                }
            }
        }).catch((err) => {
            if (err.name !== 'AbortError') {
                console.error('Stream error:', err);
            }
        });

        return () => controller.abort();
    },

    async getStats(): Promise<TokenStats> {
        const response = await fetch(`${API_BASE_URL}/chat/stats`);
        return response.json();
    },
};

// Memory API
export const memoryApi = {
    async getStats(): Promise<MemoryStats> {
        const response = await fetch(`${API_BASE_URL}/memory/stats`);
        return response.json();
    },

    async ingest(options: { days_back?: number; max_urls?: number; ecommerce_only?: boolean } = {}) {
        const response = await fetch(`${API_BASE_URL}/memory/ingest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                days_back: options.days_back ?? 30,
                max_urls: options.max_urls ?? 20,
                ecommerce_only: options.ecommerce_only ?? true,
                enrich_with_firecrawl: false,
            }),
        });
        return response.json();
    },

    async search(query: string, topK: number = 5) {
        const response = await fetch(`${API_BASE_URL}/memory/search?query=${encodeURIComponent(query)}&top_k=${topK}`);
        return response.json();
    },

    async clear() {
        const response = await fetch(`${API_BASE_URL}/memory/clear`, { method: 'DELETE' });
        return response.json();
    },
};

// Recommendations API
export const recommendationsApi = {
    async get(query?: string, category?: string, topK: number = 5): Promise<{ recommendations: Product[]; based_on: string }> {
        const params = new URLSearchParams({ top_k: String(topK) });
        if (query) params.set('query', query);
        if (category) params.set('category', category);

        const response = await fetch(`${API_BASE_URL}/recommendations?${params}`);
        return response.json();
    },

    async refresh() {
        const response = await fetch(`${API_BASE_URL}/recommendations/refresh`, { method: 'POST' });
        return response.json();
    },

    async getCategories() {
        const response = await fetch(`${API_BASE_URL}/recommendations/categories`);
        return response.json();
    },
};

// Conversations API
export const conversationsApi = {
    async list(limit: number = 20): Promise<Conversation[]> {
        const response = await fetch(`${API_BASE_URL}/conversations?limit=${limit}`);
        return response.json();
    },

    async get(id: string): Promise<Conversation> {
        const response = await fetch(`${API_BASE_URL}/conversations/${id}`);
        return response.json();
    },

    async create(title?: string): Promise<Conversation> {
        const response = await fetch(`${API_BASE_URL}/conversations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: title ?? 'New Conversation' }),
        });
        return response.json();
    },

    async addMessage(conversationId: string, role: string, content: string) {
        const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role, content }),
        });
        return response.json();
    },

    async delete(id: string) {
        const response = await fetch(`${API_BASE_URL}/conversations/${id}`, { method: 'DELETE' });
        return response.json();
    },
};

// Data API
export interface DataResponse {
    count: number;
    data: any[];
    exported_at: string;
}

export const dataApi = {
    async getBrowsing(limit: number = 100, offset: number = 0): Promise<DataResponse> {
        const response = await fetch(`${API_BASE_URL}/data/browsing?limit=${limit}&offset=${offset}`);
        return response.json();
    },

    async getProducts(limit: number = 100, offset: number = 0, category?: string): Promise<DataResponse> {
        const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
        if (category) params.set('category', category);
        const response = await fetch(`${API_BASE_URL}/data/products?${params}`);
        return response.json();
    },

    async getCategories(): Promise<{ categories: string[] }> {
        const response = await fetch(`${API_BASE_URL}/data/categories`);
        return response.json();
    },

    exportBrowsingUrl(): string {
        return `${API_BASE_URL}/data/export/browsing`;
    },

    exportProductsUrl(): string {
        return `${API_BASE_URL}/data/export/products`;
    },
};

// Health API
export const healthApi = {
    async check() {
        const response = await fetch(`${API_BASE_URL}/health`);
        return response.json();
    },
};
