import { createTheme } from '@mui/material/styles';

export function createAppTheme(mode) {
    const isDark = mode === 'dark';

    return createTheme({
        palette: {
            mode,
            primary: {
                main: isDark ? '#90caf9' : '#003B70',
                light: isDark ? '#bbdefb' : '#0055A5',
                dark: isDark ? '#1565c0' : '#002244',
            },
            secondary: {
                main: isDark ? '#4dd0e1' : '#00B4C5',
            },
            background: {
                default: isDark ? '#121a24' : '#F4F7F9',
                paper: isDark ? '#1e2935' : '#FFFFFF',
            },
            success: {
                main: isDark ? '#81c784' : '#2e7d32',
            },
            error: {
                main: isDark ? '#ef9a9a' : '#d32f2f',
            },
            warning: {
                main: isDark ? '#ffcc80' : '#ed6c02',
            },
            info: {
                main: isDark ? '#81d4fa' : '#0288d1',
            },
        },
        typography: {
            fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
            h6: { fontWeight: 600 },
            button: { textTransform: 'none', fontWeight: 600 },
        },
        shape: {
            borderRadius: 8,
        },
        components: {
            MuiAppBar: {
                styleOverrides: {
                    root: {
                        color: '#fff',
                        backgroundImage: isDark
                            ? 'linear-gradient(90deg, #172a3d 0%, #101820 100%)'
                            : 'linear-gradient(90deg, #003B70 0%, #002244 100%)',
                    },
                },
            },
            MuiButton: {
                styleOverrides: {
                    root: {
                        boxShadow: 'none',
                        '&:hover': { boxShadow: '0px 2px 8px rgba(0,0,0,0.15)' },
                    },
                },
            },
        },
    });
}
