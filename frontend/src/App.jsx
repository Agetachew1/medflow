import { Alert, Box, Card, CardContent, Container, Snackbar, Typography } from '@mui/material';
import { useEffect, useState, useContext } from 'react';

// Layout & Auth
import AppHeader from './components/layout/AppHeader.jsx';
import LoginForm from './components/auth/LoginForm.jsx';
import { AuthProvider, AuthContext } from './context/AuthContext.jsx';
import { ThemeModeProvider } from './context/ThemeModeProvider.jsx';

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
import InactiveRecordsPanel from './components/audit/InactiveRecordsPanel.jsx';
import WorkOrderHistoryGrid from './components/audit/WorkOrderHistoryGrid.jsx';

function DashboardMetrics() {
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function fetchMetrics() {
      try {
        const [equipment, lowCharge, maintenanceFlags, discrepancies] = await Promise.all([
          apiClient.get('/equipment/', { params: { page: 1, size: 1 } }),
          apiClient.get('/equipment/low-charge'),
          apiClient.get('/hospitals/maintenance-flags'),
          apiClient.get('/work-orders/discrepancies'),
        ]);
        if (isMounted) {
          setMetrics([
            { title: 'Total Equipment', value: equipment.data.total },
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
  const { user, logout, hasPermission } = useContext(AuthContext);
  const [notification, setNotification] = useState(null);
  const canManageUsers = hasPermission('users:manage');
  const canViewRoles = hasPermission('roles:read');
  const canWriteAssets = hasPermission('asset:write');
  const canReadAssignedJobs = hasPermission('job:read_assigned');
  const canReadAdvancedAnalytics = hasPermission('analytics:advanced_read');
  const canReadInactiveRecords = hasPermission('records:inactive_read');
  const canReadAudit = hasPermission('audit:read');
  const canReadAllJobs = hasPermission('job:read');

  return (
    <>
      <AppHeader
        username={user?.sub}
        role={user?.role}
        onLogout={logout}
        canManageUsers={canManageUsers}
        canViewRoles={canViewRoles}
      />
      
      <Container maxWidth="lg" sx={{ mt: 4, mb: 8 }}>
        <DashboardMetrics />

        <Typography variant="h5" component="h2" gutterBottom color="primary.main">
          Equipment Overview
        </Typography>
        <Box sx={{ mb: 4 }}>
          <EquipmentDataGrid
            onSuccess={setNotification}
            canManage={canWriteAssets}
            canViewAudit={canReadAudit}
          />
        </Box>

          {canReadInactiveRecords && <InactiveRecordsPanel />}

        {canReadAdvancedAnalytics && (
          <>
            <Typography variant="h5" component="h2" gutterBottom color="primary.main">
              Co-Location Discrepancies
            </Typography>
            <Box sx={{ mb: 4 }}>
              <DiscrepancyDataGrid />
            </Box>
          </>
        )}

        {canReadAssignedJobs && (
          <>
            <Typography variant="h5" component="h2" gutterBottom color="primary.main">
              My Work Orders
            </Typography>
            <Box sx={{ mb: 4 }}>
              <MyWorkOrders />
            </Box>
          </>
        )}

        {canReadAllJobs && canReadAudit && (
          <>
            <Typography variant="h5" component="h2" gutterBottom color="primary.main">
              Work Order History
            </Typography>
            <WorkOrderHistoryGrid />
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

        {canReadAdvancedAnalytics && (
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
  return user ? (
    <Dashboard />
  ) : (
    <>
      <AppHeader />
      <LoginForm />
    </>
  );
}

function App() {
  return (
    <ThemeModeProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ThemeModeProvider>
  );
}

export default App;