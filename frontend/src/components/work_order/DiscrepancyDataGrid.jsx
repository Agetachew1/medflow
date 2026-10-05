import { useEffect, useState } from 'react';
import { DataGrid } from '@mui/x-data-grid';
import { Alert, Box, CircularProgress, FormControl, InputLabel, MenuItem, Select } from '@mui/material';
import apiClient from "../../api/client.js";


// Map data to the DataGrid from the backend schema
const columns = [
    { field: 'work_order_id', headerName: 'Work Order ID', width: 130 },
    { field: 'title', headerName: 'Title', width: 220 },
    { field: 'equipment_hospital_id', headerName: 'Equipment Hospital', width: 160, type: 'number' },
    { field: 'technician_hospital_id', headerName: 'Technician Hospital', width: 160, type: 'number' },
];

// Ensure this matches your WorkOrderPriority enum in FastAPI
const PRIORITY_OPTIONS = ['', 'LOW', 'MEDIUM', 'CRITICAL'];

function DiscrepancyDataGrid() {
    const [priority, setPriority] = useState('');
    const [discrepancies, setDiscrepancies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let isMounted = true;
        setLoading(true);

        async function fetchDiscrepancies() {
            try {
                const response = await apiClient.get('/work-orders/discrepancies', {
                    params: { priority: priority || undefined },
                });
                if (isMounted) setDiscrepancies(response.data);
            } catch {
                if (isMounted) setError('Could not load Discrepancy report');
            } finally {
                if (isMounted) setLoading(false);
            }
        }

        fetchDiscrepancies();

        return () => {
            isMounted = false;
        };
    }, [priority]);

    return (
        <Box>
            <FormControl size="small" sx={{ mb: 2, minWidth: 180 }}>
                <InputLabel id="priority-filter-label">Priority</InputLabel>
                <Select
                    labelId="priority-filter-label"
                    label="Priority"
                    value={priority}
                    onChange={(event) => setPriority(event.target.value)}
                >
                    {PRIORITY_OPTIONS.map((option) => (
                        <MenuItem key={option || 'All'} value={option}>
                            {option === '' ? 'All' : option}
                        </MenuItem>
                    ))}
                </Select>
            </FormControl>
            {loading && <CircularProgress />}
            {error && <Alert severity="error">{error}</Alert>}
            {!loading && !error && (
                <Box sx={{ height: 400, width: '100%' }}>
                    <DataGrid
                        rows={discrepancies}
                        columns={columns}
                        getRowId={(row) => row.work_order_id} 
                        showToolbar
                        initialState={{
                            pagination: { paginationModel: { page: 0, pageSize: 5 } },
                        }}
                        pageSizeOptions={[5, 10, 25]}
                    />
                </Box>
            )}
        </Box>
    );
}

export default DiscrepancyDataGrid;