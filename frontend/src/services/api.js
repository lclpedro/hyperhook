import cacheManager from './cache';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:5001';

const api = {
    async request(endpoint, options = {}) {
        const token = localStorage.getItem('jwt_token');
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: 'Erro desconhecido.' }));
                throw new Error(errorData.message || `Erro ${response.status}`);
            }
            const contentType = response.headers.get("content-type");
            if (contentType && contentType.indexOf("application/json") !== -1) {
                return response.json();
            } else {
                return { success: true };
            }
        } catch (error) {
            console.error(`API Error on ${endpoint}:`, error);
            throw error;
        }
    },
    get(endpoint) { return this.request(endpoint, { method: 'GET' }); },
    post(endpoint, body) { return this.request(endpoint, { method: 'POST', body: JSON.stringify(body) }); },
    delete(endpoint) { return this.request(endpoint, { method: 'DELETE' }); },
    
    async getMeta() {
        const cached = cacheManager.get('hyperliquid_meta');
        if (cached) {
            console.log('Using cached Hyperliquid metadata');
            return cached;
        }
        
        console.log('Fetching fresh Hyperliquid metadata');
        const data = await this.get('/api/meta');
        cacheManager.set('hyperliquid_meta', data);
        return data;
    }
};

export default api;