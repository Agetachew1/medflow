import { useState } from 'react';
import { AppBar, Toolbar, Typography, Box, Button, IconButton, Tooltip } from '@mui/material';
import MedicalServicesIcon from '@mui/icons-material/MedicalServices';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import CreateUserModal from '../users/CreateUserModal'; 
import { useThemeMode } from '../../context/ThemeModeContext.js';

function AppHeader({ username, role, onLogout }) {
    const [isUserModalOpen, setIsUserModalOpen] = useState(false);
    const { mode, toggleMode } = useThemeMode();
    const themeToggleLabel = mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';

    return (
        <AppBar position="static">
            <Toolbar>
                <MedicalServicesIcon sx={{ mr: 2 }} />

                <Typography variant="h6" component="h1" sx={{ flexGrow: 1 }}>
                    MedFlow Command Center
                </Typography>

                <Tooltip title={themeToggleLabel}>
                    <IconButton
                        color="inherit"
                        onClick={toggleMode}
                        aria-label={themeToggleLabel}
                    >
                        {mode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
                    </IconButton>
                </Tooltip>

                {username && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Typography variant="body2">
                            {username} ({role})
                        </Typography>

                        {/* Only render the New User button for admins */}
                        {role === 'clinical_admin' && (
                            <Button color="inherit" variant="outlined" onClick={() => setIsUserModalOpen(true)}>
                                + New User
                            </Button>
                        )}

                        <Button color="inherit" onClick={onLogout}>
                            Log Out
                        </Button>
                    </Box>
                )}
            </Toolbar>

            {/* Mount the modal completely outside the Toolbar flex layout */}
            <CreateUserModal open={isUserModalOpen} onClose={() => setIsUserModalOpen(false)} />
        </AppBar>
    );
}

export default AppHeader;