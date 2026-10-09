import { useEffect, useState } from 'react';
import { DataGrid } from '@mui/x-data-grid';
import { Alert, Box, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, TextField } from '@mui/material';
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
                <Box
                    component="span"
                    sx={{
                        color: isLow ? 'error.main' : 'text.primary',
                        fontWeight: isLow ? 'bold' : 'normal',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                    }}
                >
                    {params.value}% {isLow && "⚠️"}
                </Box>
            );
        }
    },
    {
        field: 'status',
        headerName: 'Status',
        width: 170,
        renderCell: (params) => {
            const statusColors = {
                available: 'success',
                in_use: 'info',
                under_maintenance: 'warning',
                offline: 'error',
            };
            const status = String(params.value);
            return (
                <Chip
                    label={status.replaceAll('_', ' ')}
                    color={statusColors[status] || 'default'}
                    size="small"
                    sx={{ textTransform: 'capitalize' }}
                />
            );
        },
    },
    { field: 'hospital_id', headerName: 'Hospital ID', width: 110, type: 'number' },
];

const CREATE_STATUS_OPTIONS = ['ACTIVE', 'MAINTENANCE', 'RETIRED'];
const EDIT_STATUS_OPTIONS = ['AVAILABLE', 'IN_USE', 'UNDER_MAINTENANCE', 'OFFLINE'];
const EMPTY_FORM = {
    serial_number: '',
    model: '',
    charge_level: '',
    hospital_id: '',
    status: 'ACTIVE',
};

function EquipmentDataGrid({ onSuccess, canManage = false }) {
    const [equipmentList, setEquipmentList] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [dialogError, setDialogError] = useState(null);
    const [formValues, setFormValues] = useState(EMPTY_FORM);
    const [editingEquipment, setEditingEquipment] = useState(null);

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
        void fetchEquipment();
    }, []);

    const handleFieldChange = (field) => (event) => {
        setDialogError(null);
        setFormValues((prev) => ({ ...prev, [field]: event.target.value }));
    };

    const handleCreate = async () => {
        setDialogError(null);
        try {
            const payload = {
                model: formValues.model,
                status: editingEquipment
                    ? formValues.status.toLowerCase()
                    : formValues.status,
                charge_level: Number(formValues.charge_level),
                facility_id: Number(formValues.hospital_id),
            };
            if (editingEquipment) {
                await apiClient.patch(`/equipment/${editingEquipment.id}`, payload);
            } else {
                await apiClient.post('/equipment/', {
                    ...payload,
                    serial_number: formValues.serial_number,
                    hospital_id: payload.facility_id,
                });
            }
            setDialogOpen(false);
            setFormValues(EMPTY_FORM);
            if (onSuccess) {
                onSuccess(
                    editingEquipment
                        ? `Equipment ${editingEquipment.serial_number} updated.`
                        : `Equipment ${formValues.serial_number} created.`
                );
            }
            setEditingEquipment(null);
            await fetchEquipment();
        } catch (err) {
            setDialogError(err.response?.data?.detail || 'Could not save equipment.');
        }
    };

    const handleEdit = (equipment) => {
        setEditingEquipment(equipment);
        setDialogError(null);
        setFormValues({
            serial_number: equipment.serial_number,
            model: equipment.model,
            charge_level: equipment.charge_level,
            hospital_id: equipment.hospital_id,
            status: String(equipment.status).toUpperCase(),
        });
        setDialogOpen(true);
    };

    const handleDelete = async (equipment) => {
        if (!window.confirm(`Delete equipment ${equipment.serial_number}?`)) return;
        try {
            await apiClient.delete(`/equipment/${equipment.id}`);
            if (onSuccess) onSuccess(`Equipment ${equipment.serial_number} deleted.`);
            await fetchEquipment();
        } catch (err) {
            setError(err.response?.data?.detail || 'Could not delete equipment.');
        }
    };

    const gridColumns = canManage
        ? [
            ...columns,
            {
                field: 'actions',
                headerName: 'Actions',
                width: 170,
                sortable: false,
                filterable: false,
                renderCell: (params) => (
                    <Stack direction="row" spacing={1}>
                        <Button size="small" onClick={() => handleEdit(params.row)}>Edit</Button>
                        <Button size="small" color="error" onClick={() => handleDelete(params.row)}>
                            Delete
                        </Button>
                    </Stack>
                ),
            },
        ]
        : columns;

    if (loading) return <CircularProgress />;
    if (error) return <Alert severity="error">{error}</Alert>;

    return (
        <Box>
            {canManage && <Button variant="contained" color="primary" sx={{ mb: 3 }} onClick={() => {
                setDialogError(null);
                setEditingEquipment(null);
                setFormValues(EMPTY_FORM);
                setDialogOpen(true);
            }}>+ Add Equipment</Button>}
            
            <Box sx={{ height: 400, width: '100%' }}>
                <DataGrid 
                    rows={equipmentList} 
                    columns={gridColumns}
                    getRowId={(row) => row.id} 
                    showToolbar
                    initialState={{
                        pagination: { paginationModel: { page: 0, pageSize: 5 } },
                    }}
                    pageSizeOptions={[5, 10, 25]}
                    sx={{
                        border: 'none',
                        backgroundColor: 'background.paper',
                        borderRadius: 2,
                    }}
                />
            </Box>

            <Dialog open={canManage && dialogOpen} onClose={() => setDialogOpen(false)}>
                <DialogTitle>{editingEquipment ? 'Edit Equipment' : 'Add New Equipment'}</DialogTitle>
                <DialogContent>
                    <Stack spacing={2} sx={{ mt: 1, minWidth: 300 }}>
                        {dialogError && <Alert severity="error">{dialogError}</Alert>}
                        {!editingEquipment && <TextField label="Serial Number" value={formValues.serial_number} onChange={handleFieldChange('serial_number')} />}
                        <TextField label="Model" value={formValues.model} onChange={handleFieldChange('model')} />
                        <TextField label="Charge Level" type="number" value={formValues.charge_level} onChange={handleFieldChange('charge_level')} />
                        <TextField label="Hospital ID" type="number" value={formValues.hospital_id} onChange={handleFieldChange('hospital_id')} />
                        <TextField select label="Status" value={formValues.status} onChange={handleFieldChange('status')}>
                            {(editingEquipment ? EDIT_STATUS_OPTIONS : CREATE_STATUS_OPTIONS).map((option) => (
                                <MenuItem key={option} value={option}>{option.replaceAll('_', ' ')}</MenuItem>
                            ))}
                        </TextField>
                    </Stack>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => {
                        setDialogOpen(false);
                        setEditingEquipment(null);
                    }}>Cancel</Button>
                    <Button variant="contained" onClick={handleCreate}>
                        {editingEquipment ? 'Save' : 'Create'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}

export default EquipmentDataGrid;