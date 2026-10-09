import { useCallback, useEffect, useState } from 'react';
import { Alert, Box, Button, CircularProgress } from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import apiClient from '../../api/client.js';
import AuditHistoryDialog from './AuditHistoryDialog.jsx';

function WorkOrderHistoryGrid() {
    const [rows, setRows] = useState([]);
    const [rowCount, setRowCount] = useState(0);
    const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 10 });
    const [historyId, setHistoryId] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const loadWorkOrders = useCallback(async (signal) => {
        setLoading(true);
        try {
            const response = await apiClient.get('/work-orders', {
                signal,
                params: {
                    page: paginationModel.page + 1,
                    size: paginationModel.pageSize,
                },
            });
            if (signal.aborted) return;
            setRows(response.data.items);
            setRowCount(response.data.total);
            setError(null);
        } catch {
            if (!signal.aborted) setError('Could not load work-order history list.');
        } finally {
            if (!signal.aborted) setLoading(false);
        }
    }, [paginationModel]);

    useEffect(() => {
        const controller = new AbortController();
        void loadWorkOrders(controller.signal);
        return () => controller.abort();
    }, [loadWorkOrders]);

    const columns = [
        { field: 'id', headerName: 'ID', width: 80 },
        { field: 'title', headerName: 'Work Order', flex: 1, minWidth: 180 },
        { field: 'status', headerName: 'Status', width: 140 },
        {
            field: 'history',
            headerName: 'History',
            width: 120,
            sortable: false,
            filterable: false,
            renderCell: (params) => (
                <Button size="small" onClick={() => setHistoryId(params.row.id)}>
                    History
                </Button>
            ),
        },
    ];

    if (loading && rows.length === 0) return <CircularProgress />;
    if (error && rows.length === 0) return <Alert severity="error">{error}</Alert>;

    return (
        <Box sx={{ mb: 4 }}>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
            <Box sx={{ height: 400, width: '100%' }}>
                <DataGrid
                    rows={rows}
                    columns={columns}
                    rowCount={rowCount}
                    loading={loading}
                    paginationMode="server"
                    paginationModel={paginationModel}
                    onPaginationModelChange={setPaginationModel}
                    pageSizeOptions={[10, 25, 50]}
                />
            </Box>
            {historyId !== null && (
                <AuditHistoryDialog
                    open
                    recordType="job"
                    recordId={historyId}
                    onClose={() => setHistoryId(null)}
                />
            )}
        </Box>
    );
}

export default WorkOrderHistoryGrid;
