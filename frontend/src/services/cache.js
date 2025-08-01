const CACHE_DURATION = 7 * 24 * 60 * 60 * 1000;

const cacheManager = {
    set(key, data) {
        const cacheItem = {
            data,
            timestamp: Date.now(),
            expires: Date.now() + CACHE_DURATION
        };
        localStorage.setItem(`cache_${key}`, JSON.stringify(cacheItem));
    },
    
    get(key) {
        try {
            const cached = localStorage.getItem(`cache_${key}`);
            if (!cached) return null;
            
            const cacheItem = JSON.parse(cached);
            if (Date.now() > cacheItem.expires) {
                localStorage.removeItem(`cache_${key}`);
                return null;
            }
            
            return cacheItem.data;
        } catch (error) {
            console.error('Cache error:', error);
            return null;
        }
    },
    
    clear(key) {
        localStorage.removeItem(`cache_${key}`);
    }
};

export default cacheManager;