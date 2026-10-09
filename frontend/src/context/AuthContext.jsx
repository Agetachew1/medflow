import { createContext, useState, useEffect, useContext } from 'react';
import api from '../api/client.js';

export const AuthContext = createContext();

// ADDED THIS: This makes it compatible with any component calling useAuth()
export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem('access_token');
        const refreshToken = localStorage.getItem('refresh_token');
        if (token || refreshToken) {
            api.get('/auth/me')
                .then((response) => setUser(response.data))
                .catch(() => {
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    setUser(null);
                })
                .finally(() => setLoading(false));
        }
        if (!token && !refreshToken) setLoading(false);
        const handleAuthLogout = () => setUser(null);
        window.addEventListener('auth:logout', handleAuthLogout);
        return () => window.removeEventListener('auth:logout', handleAuthLogout);
    }, []);

    const login = async (username, password) => {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        try {
            const response = await api.post('/auth/token', formData, {
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            });

            const token = response.data.access_token;
            const refreshToken = response.data.refresh_token;
            localStorage.setItem('access_token', token);
            localStorage.setItem('refresh_token', refreshToken);
            const identity = await api.get('/auth/me');
            setUser(identity.data);
        } catch (error) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            setUser(null);
            console.error("Axios request failed inside AuthContext!", error);
            throw error; 
        }
    };

    const logout = async () => {
        const refreshToken = localStorage.getItem('refresh_token');
        try {
            if (refreshToken) {
                await api.post('/auth/logout', { refresh_token: refreshToken });
            }
        } catch (error) {
            console.error('Could not revoke the refresh token during logout.', error);
        } finally {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            setUser(null);
        }
    };

    const hasPermission = (permission) => user?.permissions?.includes(permission) ?? false;

    return (
        <AuthContext.Provider value={{ user, login, logout, loading, hasPermission }}>
            {!loading && children}
        </AuthContext.Provider>
    );
};