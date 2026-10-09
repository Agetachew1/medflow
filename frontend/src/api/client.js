import axios from 'axios';

const apiClient = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001'
});

let refreshRequest = null;

apiClient.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        config._accessToken = token;
        return config;
    },
    (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        const requestUrl = originalRequest?.url || '';
        const isAuthRequest = ['/auth/token', '/auth/refresh', '/auth/logout'].some(
            (path) => requestUrl.includes(path)
        );
        if (
            error.response?.status === 401
            && originalRequest?._retry
            && !isAuthRequest
        ) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.dispatchEvent(new Event('auth:logout'));
            return Promise.reject(error);
        }
        if (
            error.response?.status !== 401
            || !originalRequest
            || originalRequest._retry
            || isAuthRequest
        ) {
            return Promise.reject(error);
        }

        const currentAccessToken = localStorage.getItem('access_token');
        if (currentAccessToken && currentAccessToken !== originalRequest._accessToken) {
            originalRequest.headers = originalRequest.headers || {};
            originalRequest.headers.Authorization = `Bearer ${currentAccessToken}`;
            return apiClient(originalRequest);
        }

        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
            localStorage.removeItem('access_token');
            window.dispatchEvent(new Event('auth:logout'));
            return Promise.reject(error);
        }

        originalRequest._retry = true;
        try {
            if (!refreshRequest) {
                refreshRequest = apiClient.post('/auth/refresh', {
                    refresh_token: refreshToken,
                }).then(({ data }) => {
                    localStorage.setItem('access_token', data.access_token);
                    localStorage.setItem('refresh_token', data.refresh_token);
                    return data.access_token;
                }).finally(() => {
                    refreshRequest = null;
                });
            }
            const accessToken = await refreshRequest;
            originalRequest.headers = originalRequest.headers || {};
            originalRequest.headers.Authorization = `Bearer ${accessToken}`;
            return apiClient(originalRequest);
        } catch (refreshError) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.dispatchEvent(new Event('auth:logout'));
            return Promise.reject(refreshError);
        }
    }
);

export default apiClient;
