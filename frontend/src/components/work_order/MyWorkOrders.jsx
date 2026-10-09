import { useEffect, useState } from 'react';
import { Alert, Box, Button, CircularProgress, MenuItem, Select } from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import apiClient from '../../api/client.js';
import AuditHistoryDialog from '../audit/AuditHistoryDialog.jsx';
import { useAuth } from '../../context/AuthContext.jsx';

const STATUS_OPTIONS = ['pending', 'in_progress', 'completed', 'failed'];

function MyWorkOrders() {
    const { hasPermission } = useAuth();
    const [workOrders, setWorkOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [savingId, setSavingId] = useState(null);
    const [historyWorkOrderId, setHistoryWorkOrderId] = useState(null);

    useEffect(() => {
        async function fetchWorkOrders() {
            try {
                const response = await apiClient.get('/work-orders/mine');
                setWorkOrders(response.data);
            } catch {
                setError('Could not load your work orders.');
            } finally {
                setLoading(false);
            }
        }
        fetchWorkOrders();
    }, []);

    async function updateStatus(workOrderId, newStatus) {
        setSavingId(workOrderId);
        setError(null);
        try {
            const response = await apiClient.patch(`/work-orders/${workOrderId}/status`, {
                status: newStatus,
            });
            setWorkOrders((current) =>
                current.map((workOrder) =>
                    workOrder.id === workOrderId
                        ? { ...workOrder, status: response.data.status }
                        : workOrder
                )
            );
        } catch (err) {
            setError(err.response?.data?.detail || 'Could not update work-order status.');
        } finally {
            setSavingId(null);
        }
    }

    const columns = [
        { field: 'title', headerName: 'Work Order', flex: 1, minWidth: 180 },
        { field: 'serial_number', headerName: 'Serial Number', width: 150 },
        { field: 'model', headerName: 'Equipment Model', flex: 1, minWidth: 160 },
        {
            field: 'status',
            headerName: 'Status',
            width: 180,
            renderCell: (params) => (
                <Select
                    size="small"
                    fullWidth
                    value={params.value}
                    disabled={savingId === params.row.id}
                    onChange={(event) => updateStatus(params.row.id, event.target.value)}
                    inputProps={{ 'aria-label': `Status for work order ${params.row.id}` }}
                >
                    {STATUS_OPTIONS.map((status) => (
                        <MenuItem key={status} value={status}>
                            {status.replaceAll('_', ' ')}
                        </MenuItem>
                    ))}
                </Select>
            ),
        },
        ...(hasPermission('audit:read') ? [{
            field: 'history',
            headerName: 'History',
            width: 120,
            sortable: false,
            filterable: false,
            renderCell: (params) => (
                <Button size="small" onClick={() => setHistoryWorkOrderId(params.row.id)}>
                    History
                </Button>
            ),
        }] : []),
    ];

    if (loading) return <CircularProgress />;
    if (error && workOrders.length === 0) return <Alert severity="error">{error}</Alert>;

    return (
        <Box>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            <Box sx={{ height: 400, width: '100%' }}>
                <DataGrid
                    rows={workOrders}
                    columns={columns}
                    getRowId={(row) => row.id}
                    showToolbar
                    initialState={{
                        pagination: { paginationModel: { page: 0, pageSize: 5 } },
                    }}
                    pageSizeOptions={[5, 10, 25]}
                />
            </Box>
            {historyWorkOrderId !== null && (
                <AuditHistoryDialog
                    open
                    recordType="job"
                    recordId={historyWorkOrderId}
                    onClose={() => setHistoryWorkOrderId(null)}
                />
            )}
        </Box>
    );
}

export default MyWorkOrders;
