import { Grid } from '@mui/material';
import EquipmentCard from './EquipmentCard.jsx';

function EquipmentList({ equipmentList }) {
    return (
        <Grid container spacing={2}>
            {equipmentList.map((equipment) => (
                <Grid item key={equipment.id}>
                    <EquipmentCard equipment={equipment} />
                </Grid>
            ))}
        </Grid>
    );
}

export default EquipmentList;