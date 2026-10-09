from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db, require_permission
from backend.app.models.service_report import ServiceReport
from backend.app.models.user import User
from backend.app.permissions import Permission
from backend.app.schemas.service_report import ServiceReportCreate, ServiceReportResponse

router = APIRouter(prefix="/service-reports", tags=["Service Reports"])

@router.get("", response_model=list[ServiceReportResponse])
async def get_reports(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.REPORT_READ))
):
    result = await db.execute(select(ServiceReport))
    return result.scalars().all()

@router.post("", response_model=ServiceReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ServiceReportCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.REPORT_UPLOAD))
):
    new_report = ServiceReport(**payload.model_dump())
    
    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)
    
    return new_report