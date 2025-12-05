import { useEffect, useState } from 'react';
import { healthApi } from '../services/api';

interface HealthStatus {
    status: string;
    timestamp: string;
    service: string;
    version: string;
    config: {
        pinecone_index: string;
        embedding_model: string;
        chat_model: string;
    };
}

export const HealthCheck = () => {
    const [health, setHealth] = useState<HealthStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchHealth = async () => {
            try {
                const data = await healthApi.check();
                setHealth(data);
            } catch (err) {
                setError('Failed to connect to backend');
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchHealth();
    }, []);

    if (loading) {
        return (
            <div style={{ padding: '20px', border: '1px solid #ccc', borderRadius: '8px' }}>
                ⏳ Checking backend connection...
            </div>
        );
    }

    if (error) {
        return (
            <div style={{ padding: '20px', border: '1px solid red', borderRadius: '8px', color: 'red' }}>
                ❌ {error}
            </div>
        );
    }

    return (
        <div style={{ padding: '20px', border: '2px solid green', borderRadius: '8px', backgroundColor: '#f0fff0' }}>
            <h2 style={{ margin: '0 0 15px 0', color: 'green' }}>✅ Backend Connected</h2>
            <p><strong>Service:</strong> {health?.service}</p>
            <p><strong>Status:</strong> {health?.status}</p>
            <p><strong>Version:</strong> {health?.version}</p>
            <p><strong>Timestamp:</strong> {health?.timestamp}</p>
            <hr style={{ margin: '15px 0' }} />
            <h3>Configuration:</h3>
            <p><strong>Pinecone Index:</strong> {health?.config.pinecone_index}</p>
            <p><strong>Embedding Model:</strong> {health?.config.embedding_model}</p>
            <p><strong>Chat Model:</strong> {health?.config.chat_model}</p>
        </div>
    );
};
