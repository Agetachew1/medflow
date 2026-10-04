from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db, require_role
from backend.app.models.hospital import Hospital
from backend.app.models.equipment import Equipment
from backend.app.models.user import User
from backend.app.models.work_order import WorkOrder
from backend.app.models.enums import UserRole, WorkOrderStatus

router = APIRouter(prefix="/hospitals", tags=["hospitals"])

@router.get("/maintenance-flags")
async def get_maintenance_flags(db: AsyncSession = Depends(get_db)):
    hospitals_result = await db.execute(select(Hospital))
    hospitals = hospitals_result.scalars().all()
    
    equip_result = await db.execute(select(Equipment))
    equipments = equip_result.scalars().all()

    flags = []
    for h in hospitals:
        h_equip = [e for e in equipments if e.facility_id == h.id]
        total = len(h_equip)
        if total == 0:
            continue
            
        maint_count = sum(1 for e in h_equip if "maintenance" in str(e.status).lower() or "down" in str(e.status).lower())
        
        if (maint_count / total) >= 0.3:  
            flags.append({
                "hospital_id": h.id,
                "name": h.name,
                "total_equipment": total,
                "maintenance_count": maint_count
            })
    return flags

@router.get("/supervisors/{supervisor_id}/reporting-lines")
async def get_reporting_lines(
    supervisor_id: int, 
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.CLINICAL_ADMIN))
):
    # This query perfectly counts technicians who report to this supervisor AND have pending work orders
    statement = (
        select(func.count(func.distinct(User.id)))
        .join(Hospital, Hospital.id == User.hospital_id)
        .join(WorkOrder, WorkOrder.technician_id == User.id)
        .where(Hospital.supervisor_id == supervisor_id)
        .where(WorkOrder.status == WorkOrderStatus.PENDING)
    )
    
    result = await db.execute(statement)
    count = result.scalar() or 0
    
    return {
        "supervisor_id": supervisor_id,
        "technicians_with_active_work_orders": count
    }