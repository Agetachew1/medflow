import { useEffect, useState } from 'react';
import { Alert, CircularProgress, Dialog, DialogContent, DialogTitle, List, ListItem, ListItemText } from '@mui/material';
import apiClient from '../../api/client.js';

export default function AuditHistoryDialog({ open, onClose, recordType, recordId }) {
    const [entries, setEntries] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!open || recordId == null) return undefined;
        const controller = new AbortController();
        setLoading(true);
        setError(null);
        apiClient.get(`/audit/${recordType}/${recordId}`, { signal: controller.signal })
            .then((response) => setEntries(response.data))
            .catch(() => {
                if (!controller.signal.aborted) setError('Could not load audit history.');
            })
            .finally(() => {
                if (!controller.signal.aborted) setLoading(false);
            });
        return () => controller.abort();
    }, [open, recordId, recordType]);

    return (
        <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
            <DialogTitle>{recordType === 'asset' ? 'Asset' : 'Job'} {recordId} history</DialogTitle>
            <DialogContent>
                {loading && <CircularProgress />}
                {error && <Alert severity="error">{error}</Alert>}
                {!loading && !error && entries.length === 0 && <p>No history recorded.</p>}
                <List>
                    {entries.map((entry) => (
                        <ListItem key={entry.id} alignItems="flex-start" divider>
                            <ListItemText
                                primary={`${entry.action.replaceAll('_', ' ')} · ${entry.actor_username} · ${new Date(entry.created_at).toLocaleString()}`}
                                secondary={<pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{JSON.stringify(entry.changes, null, 2)}</pre>}
                            />
                        </ListItem>
                    ))}
                </List>
            </DialogContent>
        </Dialog>
    );
}
