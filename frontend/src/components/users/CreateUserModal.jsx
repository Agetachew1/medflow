import React, { useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Select, MenuItem, InputLabel, FormControl } from '@mui/material';
import apiClient from '../../api/client.js';

export default function CreateUserModal({ open, onClose }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [role, setRole] = useState('field_technician');
    const [hospitalId, setHospitalId] = useState('');

    const handleSubmit = async () => {
        try {
            await apiClient.post('/users/', {
                username,
                password,
                role,
                hospital_id: parseInt(hospitalId)
            });
            alert('User created successfully!');
            onClose();
        } catch (err) {
            alert(`Error: ${err.response?.data?.detail || 'Failed to create user'}`);
        }
    };

    return (
        <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
            <DialogTitle>Provision New User</DialogTitle>
            <DialogContent style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginTop: '0.5rem' }}>
                <TextField label="Username" value={username} onChange={e => setUsername(e.target.value)} fullWidth />
                <TextField label="Password" type="password" value={password} onChange={e => setPassword(e.target.value)} fullWidth />
                <FormControl fullWidth>
                    <InputLabel>Role</InputLabel>
                    <Select value={role} label="Role" onChange={e => setRole(e.target.value)}>
                        <MenuItem value="clinical_admin">Clinical Admin</MenuItem>
                        <MenuItem value="hospital_manager">Hospital Manager</MenuItem>
                        <MenuItem value="field_technician">Field Technician</MenuItem>
                        <MenuItem value="auditor">Auditor</MenuItem>
                    </Select>
                </FormControl>
                <TextField label="Hospital ID" type="number" value={hospitalId} onChange={e => setHospitalId(e.target.value)} fullWidth />
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Cancel</Button>
                <Button variant="contained" onClick={handleSubmit}>Create User</Button>
            </DialogActions>
        </Dialog>
    );
}
