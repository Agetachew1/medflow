import { useCallback, useEffect, useState } from 'react';
import { Alert, Box, Button, CircularProgress, Stack, Typography } from '@mui/material';
import apiClient from '../../api/client.js';
import AuditHistoryDialog from './AuditHistoryDialog.jsx';

function InactiveRecordsPanel() {
    const [equipment, setEquipment] = useState([]);
    const [workOrders, setWorkOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [history, setHistory] = useState(null);

    const loadInactive = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const [equipmentResponse, workOrderResponse] = await Promise.all([
                apiClient.get('/equipment/inactive'),
                apiClient.get('/work-orders/inactive'),
            ]);
            setEquipment(equipmentResponse.data);
            setWorkOrders(workOrderResponse.data);
        } catch {
            setError('Could not load inactive records.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadInactive();
    }, [loadInactive]);

    async function restore(recordType, recordId) {
        setError(null);
        try {
            await apiClient.post(`/${recordType === 'asset' ? 'equipment' : 'work-orders'}/${recordId}/restore`);
            await loadInactive();
        } catch (restoreError) {
            setError(restoreError.response?.data?.detail || 'Could not restore this record.');
        }
    }

    if (loading) return <CircularProgress />;

    return (
        <Box sx={{ mb: 4 }}>
            <Typography variant="h5" component="h2" gutterBottom color="primary.main">
                Inactive Records
            </Typography>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            <Typography variant="h6">Equipment</Typography>
            {equipment.map((record) => (
                <Stack key={`asset-${record.id}`} direction="row" spacing={1} alignItems="center" sx={{ py: 1 }}>
                    <Typography sx={{ flexGrow: 1 }}>
                        {record.serial_number} · {record.model} · deleted {record.deleted_at ? new Date(record.deleted_at).toLocaleString() : 'date unavailable'} · user {record.deleted_by ?? 'unknown'}
                    </Typography>
                    <Button onClick={() => setHistory({ type: 'asset', id: record.id })}>History</Button>
                    <Button onClick={() => restore('asset', record.id)}>Restore</Button>
                </Stack>
            ))}
            <Typography variant="h6" sx={{ mt: 2 }}>Work Orders</Typography>
            {workOrders.map((record) => (
                <Stack key={`job-${record.id}`} direction="row" spacing={1} alignItems="center" sx={{ py: 1 }}>
                    <Typography sx={{ flexGrow: 1 }}>
                        #{record.id} {record.title} · deleted {record.deleted_at ? new Date(record.deleted_at).toLocaleString() : 'date unavailable'} · user {record.deleted_by ?? 'unknown'}
                    </Typography>
                    <Button onClick={() => setHistory({ type: 'job', id: record.id })}>History</Button>
                    <Button onClick={() => restore('job', record.id)}>Restore</Button>
                </Stack>
            ))}
            {history && (
                <AuditHistoryDialog
                    open
                    recordType={history.type}
                    recordId={history.id}
                    onClose={() => setHistory(null)}
                />
            )}
        </Box>
    );
}

export default InactiveRecordsPanel;
