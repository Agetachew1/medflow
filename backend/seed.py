import asyncio
from backend.app.database import AsyncSessionLocal, engine
from backend.app.models.base import Base
from backend.app.models.hospital import Hospital
from backend.app.models.user import User
from backend.app.models.equipment import Equipment
from backend.app.models.work_order import WorkOrder
from backend.app.models.enums import UserRole, EquipmentStatus, WorkOrderStatus, WorkOrderPriority
from backend.app.security import hash_password

async def seed_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        print("Seeding database...")

        h1 = Hospital(name="Mercy General", location_region="Downtown", capacity=250, supervisor_id=1)
        h2 = Hospital(name="St. Jude's", location_region="Westside", capacity=180, supervisor_id=1)
        h3 = Hospital(name="City Health", location_region="Northside", capacity=140, supervisor_id=1)
        session.add_all([h1, h2, h3])
        await session.flush()

        admin = User(username="admin_abe", hashed_password=hash_password("securepassword123"), role=UserRole.CLINICAL_ADMIN, hospital_id=h1.id)
        manager = User(username="manager_sarah", hashed_password=hash_password("pass123"), role=UserRole.HOSPITAL_MANAGER, hospital_id=h2.id)
        tech1 = User(username="tech_john", hashed_password=hash_password("pass123"), role=UserRole.FIELD_TECHNICIAN, hospital_id=h1.id)
        tech2 = User(username="tech_mike", hashed_password=hash_password("pass123"), role=UserRole.FIELD_TECHNICIAN, hospital_id=h2.id)
        session.add_all([admin, manager, tech1, tech2])
        await session.flush()

        active_stat = EquipmentStatus.AVAILABLE
        maint_stat = EquipmentStatus.UNDER_MAINTENANCE
        low_priority = WorkOrderPriority.LOW
        high_priority = WorkOrderPriority.CRITICAL

        equipments = [
            Equipment(serial_number="MRI-001", model="Siemens Magnetom", charge_level=95, status=active_stat, facility_id=h1.id, is_active=True),
            Equipment(serial_number="XRY-002", model="GE Optima", charge_level=88, status=active_stat, facility_id=h2.id, is_active=True),
            Equipment(serial_number="ULT-003", model="Philips EPIQ", charge_level=12, status=active_stat, facility_id=h3.id, is_active=True),
            Equipment(serial_number="VEN-004", model="Medtronic Puritan", charge_level=5, status=active_stat, facility_id=h1.id, is_active=True),
            Equipment(serial_number="DEF-005", model="Zoll X Series", charge_level=100, status=maint_stat, facility_id=h2.id, is_active=True),
            Equipment(serial_number="DEF-006", model="Zoll X Series", charge_level=100, status=maint_stat, facility_id=h2.id, is_active=True),
        ]
        session.add_all(equipments)
        await session.flush()

        work_orders = [
            WorkOrder(title="Routine Calibration", equipment_id=equipments[0].id, technician_id=tech1.id, status=WorkOrderStatus.PENDING, priority=low_priority),
            WorkOrder(title="Urgent Sensor Replacement", equipment_id=equipments[2].id, technician_id=tech2.id, status=WorkOrderStatus.PENDING, priority=high_priority),
            WorkOrder(title="Screen Fix", equipment_id=equipments[1].id, technician_id=tech1.id, status=WorkOrderStatus.COMPLETED, priority=low_priority),
            WorkOrder(title="Power Supply Swap", equipment_id=equipments[1].id, technician_id=tech1.id, status=WorkOrderStatus.FAILED, priority=high_priority),
        ]
        session.add_all(work_orders)
        
        await session.commit()
        print("Database successfully seeded!")

if __name__ == "__main__":
    asyncio.run(seed_data())
