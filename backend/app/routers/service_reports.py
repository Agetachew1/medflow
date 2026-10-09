import asyncio
import logging
import os
import re
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.dependencies import get_db, require_permission
from backend.app.models.enums import UserRole
from backend.app.models.service_report import ServiceReport
from backend.app.models.user import User
from backend.app.models.work_order import WorkOrder
from backend.app.permissions import Permission
from backend.app.schemas.service_report import ServiceReportCreate, ServiceReportResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/service-reports", tags=["Service Reports"])


def _s3_client():
    client_options = {
        "region_name": settings.aws_region_name,
        "config": Config(
            connect_timeout=5,
            read_timeout=30,
            retries={"total_max_attempts": 2},
        ),
    }
    return boto3.client("s3", **client_options)


def _upload_object(file_obj, bucket: str, key: str, content_type: str) -> None:
    _s3_client().upload_fileobj(
        file_obj,
        bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )


def _delete_object(bucket: str, key: str) -> None:
    _s3_client().delete_object(Bucket=bucket, Key=key)


@router.get("", response_model=list[ServiceReportResponse])
async def get_reports(
    work_order_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.REPORT_READ)),
):
    statement = (
        select(ServiceReport)
        .join(WorkOrder, WorkOrder.id == ServiceReport.work_order_id)
        .where(WorkOrder.is_active.is_(True))
    )
    if work_order_id is not None:
        statement = statement.where(ServiceReport.work_order_id == work_order_id)
    result = await db.execute(
        statement.order_by(ServiceReport.created_at.desc(), ServiceReport.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.post(
    "",
    response_model=ServiceReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_report(
    payload: ServiceReportCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(Permission.REPORT_UPLOAD)),
):
    new_report = ServiceReport(**payload.model_dump())

    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)

    return new_report


@router.post(
    "/upload",
    response_model=ServiceReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_service_report(
    work_order_id: int = Form(..., gt=0),
    file: UploadFile = File(...),
    notes: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REPORT_UPLOAD)),
):
    if not settings.s3_bucket:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Report file storage is not configured",
        )

    work_order = await db.get(WorkOrder, work_order_id)
    if (
        work_order is None
        or not work_order.is_active
        or (
            current_user.role != UserRole.CLINICAL_ADMIN
            and work_order.technician_id != current_user.id
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active work order not found",
        )

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report file must not be empty",
        )
    if file_size > settings.max_service_report_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Report file exceeds the configured size limit",
        )

    allowed_types = ("image/", "text/plain", "application/pdf")
    if not (file.content_type or "").startswith(allowed_types):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only images, .txt and .pdf files are allowed",
        )

    suffix = os.path.splitext(file.filename or "")[1]
    safe_suffix = suffix.lower() if re.fullmatch(r"\.[A-Za-z0-9]{1,10}", suffix) else ""
    bucket = settings.s3_bucket
    object_key = f"service-reports/work-orders/{work_order_id}/{uuid4().hex}{safe_suffix}"
    content_type = file.content_type or "application/octet-stream"

    # End the read/auth transaction before waiting on S3.
    await db.rollback()
    try:
        await asyncio.to_thread(
            _upload_object,
            file.file,
            bucket,
            object_key,
            content_type,
        )
    except (BotoCoreError, ClientError) as exc:
        logger.exception("Service report upload to object storage failed")
        try:
            await asyncio.to_thread(_delete_object, bucket, object_key)
        except (BotoCoreError, ClientError):
            logger.exception("Failed to clean up an incomplete service report upload")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not store report file",
        ) from exc

    report = ServiceReport(
        work_order_id=work_order_id,
        file_url=f"s3://{bucket}/{object_key}",
        notes=notes,
    )
    db.add(report)
    try:
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        try:
            await asyncio.to_thread(_delete_object, bucket, object_key)
        except (BotoCoreError, ClientError):
            logger.exception(
                "Failed to remove uploaded service report after database failure"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not record service report",
        ) from exc

    try:
        await db.refresh(report)
    except SQLAlchemyError as exc:
        logger.exception("Service report was committed but could not be refreshed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report was saved but its record could not be reloaded",
        ) from exc

    return report