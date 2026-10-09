import { useState } from 'react';
import {
    Alert,
    Button,
    CircularProgress,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    TextField,
} from '@mui/material';
import apiClient from '../../api/client.js';

function ServiceReportUploadDialog({ open, workOrderId, onClose }) {
    const [file, setFile] = useState(null);
    const [notes, setNotes] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);

    async function submitReport(event) {
        event.preventDefault();
        if (!file) {
            setError('Choose a report file to upload.');
            return;
        }

        const formData = new FormData();
        formData.append('work_order_id', String(workOrderId));
        formData.append('file', file);
        if (notes.trim()) formData.append('notes', notes.trim());

        setLoading(true);
        setError(null);
        try {
            await apiClient.post('/service-reports/upload', formData);
            setSuccess(true);
        } catch (uploadError) {
            setError(
                uploadError.response?.data?.detail
                || 'Could not upload the service report. Please try again.'
            );
        } finally {
            setLoading(false);
        }
    }

    function closeDialog() {
        if (!loading) onClose();
    }

    return (
        <Dialog open={open} onClose={closeDialog} fullWidth maxWidth="sm">
            <form onSubmit={submitReport}>
                <DialogTitle>Upload Service Report</DialogTitle>
                <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '8px !important' }}>
                    {success ? (
                        <Alert severity="success">
                            Service report uploaded for work order {workOrderId}.
                        </Alert>
                    ) : (
                        <>
                            <Alert severity="info">
                                Attach an image, PDF, or text report to work order {workOrderId}.
                            </Alert>
                            {error && <Alert severity="error">{error}</Alert>}
                            <TextField
                                type="file"
                                label="Report file"
                                required
                                fullWidth
                                slotProps={{
                                    htmlInput: { accept: 'image/*,.pdf,.txt' },
                                }}
                                onChange={(event) => {
                                    setFile(event.target.files?.[0] || null);
                                    setError(null);
                                }}
                            />
                            <TextField
                                label="Notes (optional)"
                                value={notes}
                                onChange={(event) => setNotes(event.target.value)}
                                multiline
                                minRows={2}
                                fullWidth
                            />
                        </>
                    )}
                </DialogContent>
                <DialogActions>
                    <Button onClick={closeDialog} disabled={loading}>
                        {success ? 'Done' : 'Cancel'}
                    </Button>
                    {!success && (
                        <Button type="submit" variant="contained" disabled={loading || !file}>
                            {loading ? <CircularProgress size={22} color="inherit" /> : 'Upload'}
                        </Button>
                    )}
                </DialogActions>
            </form>
        </Dialog>
    );
}

export default ServiceReportUploadDialog;
