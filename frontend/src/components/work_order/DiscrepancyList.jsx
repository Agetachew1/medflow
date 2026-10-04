import { Grid } from '@mui/material';
import DiscrepancyCard from './DiscrepancyCard.jsx';

function DiscrepancyList({ discrepancies }) {
    return (
        <Grid container spacing={2}>
            {discrepancies.map((discrepancy) => (
                <Grid item key={discrepancy.work_order_id}>
                    <DiscrepancyCard discrepancy={discrepancy} />
                </Grid>
            ))}
        </Grid>
    );
}

export default DiscrepancyList;