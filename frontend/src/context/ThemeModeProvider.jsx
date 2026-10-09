import { useCallback, useMemo, useState } from 'react';
import { CssBaseline, ThemeProvider, useMediaQuery } from '@mui/material';
import { createAppTheme } from '../theme.js';
import { ThemeModeContext } from './ThemeModeContext.js';

const STORAGE_KEY = 'medflow-color-mode';

function readStoredMode() {
    try {
        const mode = window.localStorage.getItem(STORAGE_KEY);
        return mode === 'light' || mode === 'dark' ? mode : null;
    } catch {
        return null;
    }
}

export function ThemeModeProvider({ children }) {
    const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)', { noSsr: true });
    const [storedMode, setStoredMode] = useState(readStoredMode);
    const mode = storedMode ?? (prefersDarkMode ? 'dark' : 'light');

    const toggleMode = useCallback(() => {
        const nextMode = mode === 'dark' ? 'light' : 'dark';
        setStoredMode(nextMode);
        try {
            window.localStorage.setItem(STORAGE_KEY, nextMode);
        } catch {
            // The in-memory choice still applies when browser storage is unavailable.
        }
    }, [mode]);

    const theme = useMemo(() => createAppTheme(mode), [mode]);
    const contextValue = useMemo(() => ({ mode, toggleMode }), [mode, toggleMode]);

    return (
        <ThemeModeContext.Provider value={contextValue}>
            <ThemeProvider theme={theme}>
                <CssBaseline />
                {children}
            </ThemeProvider>
        </ThemeModeContext.Provider>
    );
}
