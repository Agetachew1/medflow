import { useEffect, useState } from 'react';
import { Alert, CircularProgress, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material';
import apiClient from '../../api/client.js';

function LowChargeAlert() {
    const [equipment, setEquipment] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function fetchLowCharge() {
            try {
                const response = await apiClient.get('/equipment/low-charge');
                setEquipment(response.data);
            } catch {
                setError('Could not load low-charge equipment.');
            } finally {
                setLoading(false);
            }
        }
        fetchLowCharge();
    }, []);

    if (loading) return <CircularProgress />;
    if (error) return <Alert severity="error">{error}</Alert>;
    if (equipment.length === 0) {
        return <Alert severity="success">No active equipment is below 20% charge.</Alert>;
    }

    return (
        <TableContainer component={Paper}>
            <Table size="small">
                <TableHead>
                    <TableRow>
                        <TableCell>Serial Number</TableCell>
                        <TableCell>Model</TableCell>
                        <TableCell align="right">Charge</TableCell>
                        <TableCell>Hospital</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {equipment.map((row) => (
                        <TableRow key={row.id}>
                            <TableCell>{row.serial_number}</TableCell>
                            <TableCell>{row.model}</TableCell>
                            <TableCell align="right">{row.charge_level}%</TableCell>
                            <TableCell>{row.hospital}</TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );
}

export default LowChargeAlert;
