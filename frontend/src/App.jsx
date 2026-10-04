import { Container, Typography, Box, Snackbar, Alert, ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import { useState, useContext } from 'react';

// Layout & Auth
import AppHeader from './components/layout/AppHeader.jsx';
import LoginForm from './components/auth/LoginForm.jsx';
import { AuthProvider, AuthContext } from './context/AuthContext.jsx';

// Data Grids
import EquipmentDataGrid from './components/equipments/EquipmentDataGrid.jsx';
import DiscrepancyDataGrid from './components/work_order/DiscrepancyDataGrid.jsx';

// Analytics Panels
import ReliabilityMetrics from './components/analytics/ReliabilityMetrics.jsx';
import MaintenanceFlags from './components/analytics/MaintenanceFlags.jsx';
import ReportingLines from './components/analytics/ReportingLines.jsx';

const corporateTheme = createTheme({
    palette: {
        mode: 'light',
        primary: {
            main: '#003B70',
            light: '#0055A5',
        },
        secondary: {
            main: '#00B4C5',
        },
        background: {
            default: '#F4F7F9',
            paper: '#FFFFFF',
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
                    boxShadow: '0px 2px 10px rgba(0,0,0,0.08)',
                    background: 'linear-gradient(90deg, #003B70 0%, #002244 100%)',
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

function Dashboard() {
  const { user, logout } = useContext(AuthContext);
  const [notification, setNotification] = useState(null);

  return (
    <>
      <AppHeader username={user?.sub} role={user?.role} onLogout={logout} />
      
      <Container maxWidth="lg" sx={{ mt: 4, mb: 8 }}>
        <Typography variant="h5" component="h2" gutterBottom color="primary.main">
          Equipment Overview
        </Typography>
        <Box sx={{ mb: 4 }}>
          <EquipmentDataGrid onSuccess={setNotification} />
        </Box>

        <Typography variant="h5" component="h2" gutterBottom color="primary.main">
          Co-Location Discrepancies
        </Typography>
        <Box sx={{ mb: 4 }}>
          <DiscrepancyDataGrid />
        </Box>

        <Typography variant="h5" component="h2" gutterBottom color="primary.main">
          Reliability Metrics
        </Typography>
        <Box sx={{ mb: 4 }}>
          <ReliabilityMetrics />
        </Box>

        <Typography variant="h5" component="h2" gutterBottom color="primary.main">
          Maintenance Flags
        </Typography>
        <Box sx={{ mb: 4 }}>
          <MaintenanceFlags />
        </Box>

        <Typography variant="h5" component="h2" gutterBottom color="primary.main">
          Reporting Lines
        </Typography>
        <Box sx={{ mb: 4 }}>
          <ReportingLines />
        </Box>
      </Container>

      <Snackbar
        open={Boolean(notification)}
        autoHideDuration={4000}
        onClose={() => setNotification(null)}
      >
        <Alert severity="success" onClose={() => setNotification(null)}>
          {notification}
        </Alert>
      </Snackbar>
    </>
  );
}

function AppContent() {
  const { user } = useContext(AuthContext);
  return user ? <Dashboard /> : <LoginForm />;
}

function App() {
  return (
    <ThemeProvider theme={corporateTheme}>
      <CssBaseline />
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;