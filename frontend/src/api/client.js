import axios from 'axios';

// Create a global axios instance with default configuration
const apiClient = axios.create({
    baseURL: 'http://127.0.0.1:8001'
});

// The Interceptor will be called before every request is sent
apiClient.interceptors.request.use(
    (config) => {
        // Get the token from localStorage
        const token = localStorage.getItem('access_token');

        // If the token exists, add it to the Authorization header
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }

        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

export default apiClient;