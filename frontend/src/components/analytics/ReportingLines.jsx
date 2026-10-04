import { useState } from 'react';
import { Alert, Box, Button, TextField, Typography } from '@mui/material';
import apiClient from "../../api/client.js";

function ReportingLines() {
    const [supervisorId, setSupervisorId] = useState('');
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    const handleLookup = async () => {
        if (!supervisorId) return;
        setError(null);
        setResult(null);
        try {
            const response = await apiClient.get(`/hospitals/supervisors/${supervisorId}/reporting-lines`);
            setResult(response.data);
        } catch {
            setError('Could not load reporting line data for that supervisor ID.');
        }
    };

    return (
        <Box>
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <TextField
                    label="Supervisor ID"
                    size="small"
                    value={supervisorId}
                    onChange={(event) => setSupervisorId(event.target.value)}
                />
                <Button variant="contained" onClick={handleLookup}>Look Up</Button>
            </Box>

            {error && <Alert severity="error">{error}</Alert>}

            {result && (
                <Alert severity="info">
                    Supervisor {result.supervisor_id}: {result.technicians_with_active_work_orders} technician(s) with active work orders.
                </Alert>
            )}
        </Box>
    );
}

export default ReportingLines;