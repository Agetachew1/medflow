import { Alert, Box, Card, CardContent, Container, CssBaseline, Snackbar, ThemeProvider, Typography, createTheme } from '@mui/material';
import { useEffect, useState, useContext } from 'react';

// Layout & Auth
import AppHeader from './components/layout/AppHeader.jsx';
import LoginForm from './components/auth/LoginForm.jsx';
import { AuthProvider, AuthContext } from './context/AuthContext.jsx';

// Data Grids
import EquipmentDataGrid from './components/equipments/EquipmentDataGrid.jsx';
import LowChargeAlert from './components/equipments/LowChargeAlert.jsx';
import DiscrepancyDataGrid from './components/work_order/DiscrepancyDataGrid.jsx';
import MyWorkOrders from './components/work_order/MyWorkOrders.jsx';
import apiClient from './api/client.js';

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

function DashboardMetrics() {
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function fetchMetrics() {
      try {
        const [equipment, lowCharge, maintenanceFlags, discrepancies] = await Promise.all([
          apiClient.get('/equipment/'),
          apiClient.get('/equipment/low-charge'),
          apiClient.get('/hospitals/maintenance-flags'),
          apiClient.get('/work-orders/discrepancies'),
        ]);
        if (isMounted) {
          setMetrics([
            { title: 'Total Equipment', value: equipment.data.length },
            { title: 'Low Charge (<20%)', value: lowCharge.data.length },
            { title: 'Hospitals Flagged', value: maintenanceFlags.data.length },
            { title: 'Co-Location Discrepancies', value: discrepancies.data.length },
          ]);
        }
      } catch {
        if (isMounted) setError('Could not load dashboard metrics.');
      }
    }
    fetchMetrics();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 2, mb: 4 }}>
        {(metrics || [
          { title: 'Total Equipment', value: '—' },
          { title: 'Low Charge (<20%)', value: '—' },
          { title: 'Hospitals Flagged', value: '—' },
          { title: 'Co-Location Discrepancies', value: '—' },
        ]).map((metric) => (
          <Card key={metric.title}>
            <CardContent>
              <Typography color="text.secondary" variant="body2">{metric.title}</Typography>
              <Typography color="primary.main" variant="h4" sx={{ mt: 1 }}>
                {metric.value}
              </Typography>
            </CardContent>
          </Card>
        ))}
      </Box>
    </>
  );
}

function Dashboard() {
  const { user, logout } = useContext(AuthContext);
  const [notification, setNotification] = useState(null);
  const isAdmin = user?.role === 'clinical_admin';
  const isTechnician = user?.role === 'field_technician';

  return (
    <>
      <AppHeader username={user?.sub} role={user?.role} onLogout={logout} />
      
      <Container maxWidth="lg" sx={{ mt: 4, mb: 8 }}>
        <DashboardMetrics />

        <Typography variant="h5" component="h2" gutterBottom color="primary.main">
          Equipment Overview
        </Typography>
        <Box sx={{ mb: 4 }}>
          <EquipmentDataGrid onSuccess={setNotification} canManage={isAdmin} />
        </Box>

        {isAdmin && (
          <>
            <Typography variant="h5" component="h2" gutterBottom color="primary.main">
              Co-Location Discrepancies
            </Typography>
            <Box sx={{ mb: 4 }}>
              <DiscrepancyDataGrid />
            </Box>
          </>
        )}

        {isTechnician && (
          <>
            <Typography variant="h5" component="h2" gutterBottom color="primary.main">
              My Work Orders
            </Typography>
            <Box sx={{ mb: 4 }}>
              <MyWorkOrders />
            </Box>
          </>
        )}

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
          Low Charge Alerts
        </Typography>
        <Box sx={{ mb: 4 }}>
          <LowChargeAlert />
        </Box>

        {isAdmin && (
          <>
            <Typography variant="h5" component="h2" gutterBottom color="primary.main">
              Reporting Lines
            </Typography>
            <Box sx={{ mb: 4 }}>
              <ReportingLines />
            </Box>
          </>
        )}
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