import { useCallback, useEffect, useState } from 'react';
import { DataGrid } from '@mui/x-data-grid';
import { Alert, Box, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, FormControl, InputLabel, MenuItem, Select, Stack, TextField } from '@mui/material';
import apiClient from "../../api/client.js";
import AuditHistoryDialog from '../audit/AuditHistoryDialog.jsx';

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

function EquipmentDataGrid({ onSuccess, canManage = false, canViewAudit = false }) {
    const [equipmentList, setEquipmentList] = useState([]);
    const [rowCount, setRowCount] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [search, setSearch] = useState('');
    const [debouncedSearch, setDebouncedSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [siteId, setSiteId] = useState('');
    const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 10 });
    const [sortModel, setSortModel] = useState([{ field: 'id', sort: 'asc' }]);
    const [reloadToken, setReloadToken] = useState(0);
    const [dialogOpen, setDialogOpen] = useState(false);
    const [dialogError, setDialogError] = useState(null);
    const [formValues, setFormValues] = useState(EMPTY_FORM);
    const [editingEquipment, setEditingEquipment] = useState(null);
    const [historyEquipment, setHistoryEquipment] = useState(null);

    const fetchEquipment = useCallback(async (signal) => {
        setLoading(true);
        try {
            const sort = sortModel[0];
            const response = await apiClient.get('/equipment/', {
                signal,
                params: {
                    page: paginationModel.page + 1,
                    size: paginationModel.pageSize,
                    search: debouncedSearch || undefined,
                    status: statusFilter || undefined,
                    site_id: siteId || undefined,
                    sort_by: sort?.field === 'hospital_id' ? 'site_id' : (sort?.field || 'id'),
                    sort_dir: sort?.sort || 'asc',
                },
            });
            if (signal?.aborted) return;
            setEquipmentList(response.data.items);
            setRowCount(response.data.total);
            setError(null);
        } catch {
            if (!signal?.aborted) setError('Could not load equipment data.');
        } finally {
            if (!signal?.aborted) setLoading(false);
        }
    }, [debouncedSearch, paginationModel, siteId, sortModel, statusFilter]);

    useEffect(() => {
        const timeout = window.setTimeout(() => setDebouncedSearch(search.trim()), 300);
        return () => window.clearTimeout(timeout);
    }, [search]);

    useEffect(() => {
        const controller = new AbortController();
        void fetchEquipment(controller.signal);
        return () => controller.abort();
    }, [fetchEquipment, reloadToken]);

    const handleFilterChange = (setter) => (event) => {
        setter(event.target.value);
        setPaginationModel((current) => ({ ...current, page: 0 }));
    };

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
            setReloadToken((current) => current + 1);
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
            setReloadToken((current) => current + 1);
        } catch (err) {
            setError(err.response?.data?.detail || 'Could not delete equipment.');
        }
    };

    const gridColumns = [
        ...columns,
        {
            field: 'actions',
            headerName: 'Actions',
            width: canManage ? 250 : 100,
            sortable: false,
            filterable: false,
            renderCell: (params) => (
                <Stack direction="row" spacing={1}>
                    {canViewAudit && <Button size="small" onClick={() => setHistoryEquipment(params.row)}>History</Button>}
                    {canManage && <Button size="small" onClick={() => handleEdit(params.row)}>Edit</Button>}
                    {canManage && (
                        <Button size="small" color="error" onClick={() => handleDelete(params.row)}>
                            Delete
                        </Button>
                    )}
                </Stack>
            ),
        },
    ];

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

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
                <TextField
                    label="Search model or serial number"
                    value={search}
                    onChange={handleFilterChange(setSearch)}
                    size="small"
                />
                <FormControl size="small" sx={{ minWidth: 180 }}>
                    <InputLabel id="equipment-status-filter-label">Status</InputLabel>
                    <Select
                        labelId="equipment-status-filter-label"
                        label="Status"
                        value={statusFilter}
                        onChange={handleFilterChange(setStatusFilter)}
                    >
                        <MenuItem value="">All statuses</MenuItem>
                        {EDIT_STATUS_OPTIONS.map((option) => (
                            <MenuItem key={option} value={option.toLowerCase()}>
                                {option.replaceAll('_', ' ')}
                            </MenuItem>
                        ))}
                    </Select>
                </FormControl>
                <TextField
                    label="Hospital ID"
                    type="number"
                    value={siteId}
                    onChange={handleFilterChange(setSiteId)}
                    size="small"
                    slotProps={{ htmlInput: { min: 1 } }}
                />
            </Stack>
            
            <Box sx={{ height: 400, width: '100%' }}>
                <DataGrid 
                    rows={equipmentList} 
                    columns={gridColumns}
                    getRowId={(row) => row.id} 
                    showToolbar
                    rowCount={rowCount}
                    paginationMode="server"
                    sortingMode="server"
                    filterMode="server"
                    paginationModel={paginationModel}
                    onPaginationModelChange={setPaginationModel}
                    sortModel={sortModel}
                    onSortModelChange={setSortModel}
                    pageSizeOptions={[10, 25, 50]}
                    disableColumnFilter
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
            {historyEquipment && (
                <AuditHistoryDialog
                    open
                    recordType="asset"
                    recordId={historyEquipment.id}
                    onClose={() => setHistoryEquipment(null)}
                />
            )}
        </Box>
    );
}

export default EquipmentDataGrid;