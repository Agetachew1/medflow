import { useEffect, useState } from 'react';
import { DataGrid } from '@mui/x-data-grid';
import { Alert, Box, CircularProgress, Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField } from '@mui/material';
import apiClient from "../../api/client.js";

const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'serial_number', headerName: 'Serial Number', width: 150 },
    { field: 'model', headerName: 'Model', width: 160 },
    { 
        field: 'charge_level', 
        headerName: 'Charge %', 
        width: 120, 
        type: 'number',
        renderCell: (params) => {
            const isLow = params.value < 20;
            return (
                <span style={{ 
                    color: isLow ? '#d32f2f' : 'inherit', 
                    fontWeight: isLow ? 'bold' : 'normal',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                }}>
                    {params.value}% {isLow && "⚠️"}
                </span>
            );
        }
    },
    { field: 'status', headerName: 'Status', width: 130 },
    { field: 'hospital_id', headerName: 'Hospital ID', width: 110, type: 'number' },
];

const STATUS_OPTIONS = ['ACTIVE', 'MAINTENANCE', 'RETIRED'];

function EquipmentDataGrid({ onSuccess }) {
    const [equipmentList, setEquipmentList] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [dialogError, setDialogError] = useState(null);
    const [formValues, setFormValues] = useState({
        serial_number: '',
        model: '',
        charge_level: '',
        hospital_id: '',
        status: 'ACTIVE',
    });

    async function fetchEquipment() {
        setLoading(true);
        try {
            const response = await apiClient.get('/equipment/');
            setEquipmentList(response.data);
            setError(null);
        } catch {
            setError('Could not load equipment data.');
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        fetchEquipment();
    }, []);

    const handleFieldChange = (field) => (event) => {
        setDialogError(null);
        setFormValues((prev) => ({ ...prev, [field]: event.target.value }));
    };

    const handleCreate = async () => {
        setDialogError(null);
        try {
            await apiClient.post('/equipment/', {
                ...formValues,
                charge_level: Number(formValues.charge_level),
                hospital_id: Number(formValues.hospital_id),
            });
            setDialogOpen(false);
            setFormValues({ serial_number: '', model: '', charge_level: '', hospital_id: '', status: 'ACTIVE' });
            if (onSuccess) onSuccess(`Equipment ${formValues.serial_number} created.`);
            await fetchEquipment();
        } catch (err) {
            setDialogError(err.response?.data?.detail || 'Could not create equipment.');
        }
    };

    if (loading) return <CircularProgress />;
    if (error) return <Alert severity="error">{error}</Alert>;

    return (
        <Box>
            <Button variant="contained" color="primary" sx={{ mb: 3 }} onClick={() => {
                setDialogError(null);
                setDialogOpen(true);
            }}>+ Add Equipment</Button>
            
            <Box sx={{ height: 400, width: '100%' }}>
                <DataGrid 
                    rows={equipmentList} 
                    columns={columns} 
                    getRowId={(row) => row.id} 
                    sx={{
                        border: 'none',
                        backgroundColor: 'white',
                        boxShadow: '0px 4px 20px rgba(0,0,0,0.04)',
                        borderRadius: 2,
                        '& .MuiDataGrid-columnHeaders': {
                            backgroundColor: '#FAFAFB',
                            color: '#4A5568',
                            fontWeight: 700,
                            borderBottom: '2px solid #EDF2F7',
                        },
                        '& .MuiDataGrid-row:hover': {
                            backgroundColor: '#F7FAFC',
                        },
                        '& .MuiDataGrid-cell': {
                            borderBottom: '1px solid #EDF2F7',
                        },
                    }}
                />
            </Box>

            <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
                <DialogTitle>Add New Equipment</DialogTitle>
                <DialogContent>
                    <Stack spacing={2} sx={{ mt: 1, minWidth: 300 }}>
                        {dialogError && <Alert severity="error">{dialogError}</Alert>}
                        <TextField label="Serial Number" value={formValues.serial_number} onChange={handleFieldChange('serial_number')} />
                        <TextField label="Model" value={formValues.model} onChange={handleFieldChange('model')} />
                        <TextField label="Charge Level" type="number" value={formValues.charge_level} onChange={handleFieldChange('charge_level')} />
                        <TextField label="Hospital ID" type="number" value={formValues.hospital_id} onChange={handleFieldChange('hospital_id')} />
                        <TextField select label="Status" value={formValues.status} onChange={handleFieldChange('status')}>
                            {STATUS_OPTIONS.map((option) => (
                                <MenuItem key={option} value={option}>{option}</MenuItem>
                            ))}
                        </TextField>
                    </Stack>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
                    <Button variant="contained" onClick={handleCreate}>Create</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}

export default EquipmentDataGrid;