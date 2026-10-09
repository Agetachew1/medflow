import { useState } from 'react';
import { Alert, AppBar, Box, Button, CircularProgress, Dialog, DialogContent, DialogTitle, IconButton, List, ListItem, ListItemText, Toolbar, Tooltip, Typography } from '@mui/material';
import MedicalServicesIcon from '@mui/icons-material/MedicalServices';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import CreateUserModal from '../users/CreateUserModal'; 
import { useThemeMode } from '../../context/ThemeModeContext.js';
import apiClient from '../../api/client.js';

function AppHeader({ username, role, onLogout, canManageUsers = false, canViewRoles = false }) {
    const [isUserModalOpen, setIsUserModalOpen] = useState(false);
    const [isRolesDialogOpen, setIsRolesDialogOpen] = useState(false);
    const [roles, setRoles] = useState([]);
    const [rolesLoading, setRolesLoading] = useState(false);
    const [rolesError, setRolesError] = useState(null);
    const { mode, toggleMode } = useThemeMode();
    const themeToggleLabel = mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';

    const openRoles = async () => {
        setIsRolesDialogOpen(true);
        setRolesLoading(true);
        setRolesError(null);
        try {
            const response = await apiClient.get('/roles');
            setRoles(response.data);
        } catch {
            setRolesError('Could not load role permissions.');
        } finally {
            setRolesLoading(false);
        }
    };

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

                        {canViewRoles && (
                            <Button color="inherit" onClick={openRoles}>
                                Roles &amp; Permissions
                            </Button>
                        )}

                        {canManageUsers && (
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

            <Dialog open={isRolesDialogOpen} onClose={() => setIsRolesDialogOpen(false)} fullWidth maxWidth="sm">
                <DialogTitle>Roles &amp; Permissions</DialogTitle>
                <DialogContent>
                    {rolesLoading && <CircularProgress />}
                    {rolesError && <Alert severity="error">{rolesError}</Alert>}
                    {!rolesLoading && !rolesError && roles.map((item) => (
                        <List key={item.role} dense>
                            <ListItem>
                                <ListItemText
                                    primary={item.role.replaceAll('_', ' ')}
                                    secondary={item.permissions.map((permission) => permission.replaceAll(':', ' · ')).join(', ')}
                                />
                            </ListItem>
                        </List>
                    ))}
                </DialogContent>
            </Dialog>
        </AppBar>
    );
}

export default AppHeader;