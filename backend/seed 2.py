import argparse
import asyncio
import os

from sqlalchemy import delete, select, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.database import AsyncSessionLocal, engine
from backend.app.models.base import Base
from backend.app.models.equipment import Equipment
from backend.app.models.enums import (
    EquipmentStatus,
    UserRole,
    WorkOrderPriority,
    WorkOrderStatus,
)
from backend.app.models.hospital import Hospital
from backend.app.models.service_report import ServiceReport
from backend.app.models.user import User
from backend.app.models.work_order import WorkOrder
from backend.app.security import hash_password

HOSPITALS = (
    ("Mercy General", "Downtown", 250),
    ("St. Jude's", "Westside", 180),
    ("City Health", "Northside", 140),
)

USERS = (
    ("admin_abe", UserRole.CLINICAL_ADMIN, "Mercy General"),
    ("tech_john", UserRole.FIELD_TECHNICIAN, "Mercy General"),
    ("tech_mike", UserRole.FIELD_TECHNICIAN, "St. Jude's"),
)

EQUIPMENT = (
    ("MRI-001", "Siemens Magnetom", 95, EquipmentStatus.AVAILABLE, "Mercy General"),
    ("XRY-002", "GE Optima", 88, EquipmentStatus.AVAILABLE, "St. Jude's"),
    ("ULT-003", "Philips EPIQ", 12, EquipmentStatus.AVAILABLE, "City Health"),
    ("VEN-004", "Medtronic Puritan", 5, EquipmentStatus.AVAILABLE, "Mercy General"),
    ("DEF-005", "Zoll X Series", 100, EquipmentStatus.UNDER_MAINTENANCE, "St. Jude's"),
    ("DEF-006", "Zoll X Series", 100, EquipmentStatus.UNDER_MAINTENANCE, "St. Jude's"),
)

WORK_ORDERS = (
    ("Routine Calibration", "MRI-001", "tech_john", WorkOrderStatus.PENDING, WorkOrderPriority.LOW),
    ("Urgent Sensor Replacement", "ULT-003", "tech_mike", WorkOrderStatus.IN_PROGRESS, WorkOrderPriority.CRITICAL),
    ("Screen Fix", "XRY-002", "tech_john", WorkOrderStatus.COMPLETED, WorkOrderPriority.LOW),
    ("Power Supply Swap", "XRY-002", "tech_john", WorkOrderStatus.FAILED, WorkOrderPriority.CRITICAL),
)

HOSPITAL_NAMES = tuple(record[0] for record in HOSPITALS)
USERNAMES = tuple(record[0] for record in USERS)
SERIAL_NUMBERS = tuple(record[0] for record in EQUIPMENT)
WORK_ORDER_TITLES = tuple(record[0] for record in WORK_ORDERS)


async def reset_seed_data(session) -> None:
    equipment_ids = select(Equipment.id).where(Equipment.serial_number.in_(SERIAL_NUMBERS))
    technician_ids = select(User.id).where(User.username.in_(USERNAMES))
    work_order_ids = select(WorkOrder.id).where(
        WorkOrder.title.in_(WORK_ORDER_TITLES),
        WorkOrder.equipment_id.in_(equipment_ids),
        WorkOrder.technician_id.in_(technician_ids),
    )
    await session.execute(
        delete(ServiceReport).where(ServiceReport.work_order_id.in_(work_order_ids))
    )
    await session.execute(delete(WorkOrder).where(WorkOrder.id.in_(work_order_ids)))
    await session.execute(
        delete(Equipment).where(Equipment.serial_number.in_(SERIAL_NUMBERS))
    )
    await session.execute(delete(User).where(User.username.in_(USERNAMES)))
    await session.execute(
        delete(Hospital).where(Hospital.name.in_(HOSPITAL_NAMES))
    )


async def seed_data(reset: bool = False) -> None:
    database_url = os.environ.get("DATABASE_URL")
    seed_password = os.environ.get("SEED_USER_PASSWORD")
    if not database_url:
        raise ValueError("DATABASE_URL is required.")
    if not seed_password:
        raise ValueError("SEED_USER_PASSWORD is required.")

    try:
        await asyncio.wait_for(
            _check_database_connection(),
            timeout=6,
        )
        async with asyncio.timeout(20):
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)

            async with AsyncSessionLocal() as session, session.begin():
                if reset:
                    await reset_seed_data(session)

                hospitals: dict[str, Hospital] = {}
                for name, region, capacity in HOSPITALS:
                    hospital = await session.scalar(
                        select(Hospital).where(Hospital.name == name)
                    )
                    if hospital is None:
                        hospital = Hospital(
                            name=name,
                            location_region=region,
                            capacity=capacity,
                            supervisor_id=1,
                        )
                        session.add(hospital)
                    else:
                        hospital.location_region = region
                        hospital.capacity = capacity
                    hospitals[name] = hospital
                await session.flush()

                users: dict[str, User] = {}
                password_hash = hash_password(seed_password)
                for username, role, hospital_name in USERS:
                    user = await session.scalar(
                        select(User).where(User.username == username)
                    )
                    if user is None:
                        user = User(
                            username=username,
                            hashed_password=password_hash,
                            role=role,
                            hospital_id=hospitals[hospital_name].id,
                        )
                        session.add(user)
                    else:
                        user.role = role
                        user.hospital_id = hospitals[hospital_name].id
                        if reset:
                            user.hashed_password = password_hash
                    users[username] = user
                await session.flush()

                equipment_by_serial: dict[str, Equipment] = {}
                for serial, model, charge, status, hospital_name in EQUIPMENT:
                    equipment = await session.scalar(
                        select(Equipment).where(Equipment.serial_number == serial)
                    )
                    if equipment is None:
                        equipment = Equipment(
                            serial_number=serial,
                            model=model,
                            charge_level=charge,
                            status=status,
                            facility_id=hospitals[hospital_name].id,
                            is_active=True,
                        )
                        session.add(equipment)
                    else:
                        equipment.model = model
                        equipment.charge_level = charge
                        equipment.status = status
                        equipment.facility_id = hospitals[hospital_name].id
                        equipment.is_active = True
                    equipment_by_serial[serial] = equipment
                await session.flush()

                for title, serial, username, status, priority in WORK_ORDERS:
                    equipment = equipment_by_serial[serial]
                    technician = users[username]
                    work_order = await session.scalar(
                        select(WorkOrder).where(
                            WorkOrder.title == title,
                            WorkOrder.equipment_id == equipment.id,
                            WorkOrder.technician_id == technician.id,
                        )
                    )
                    if work_order is None:
                        session.add(
                            WorkOrder(
                                title=title,
                                equipment_id=equipment.id,
                                technician_id=technician.id,
                                status=status,
                                priority=priority,
                            )
                        )
                    else:
                        work_order.status = status
                        work_order.priority = priority
    except (SQLAlchemyError, OSError, TimeoutError) as exc:
        raise RuntimeError(
            f"Database setup or seed operation failed ({type(exc).__name__})."
        ) from None


async def _check_database_connection() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Idempotently seed MedFlow demo data.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear known demo records and load them again.",
    )
    args = parser.parse_args()
    try:
        asyncio.run(seed_data(reset=args.reset))
    except (RuntimeError, ValueError) as exc:
        print(f"Seed failed: {exc}", file=os.sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
