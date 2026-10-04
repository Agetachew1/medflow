
from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import Boolean, CheckConstraint, Enum as SqlEnum, ForeignKey, Integer, String, Numeric
from backend.app.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.enums import EquipmentStatus


if TYPE_CHECKING:
    from backend.app.models.hospital import Hospital
    from backend.app.models.work_order import WorkOrder
    
class Equipment(Base):
    __tablename__ = "equipments"
    
    __table_args__ = (
        CheckConstraint("charge_level BETWEEN 0 AND 100", name="charge_level_range"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    serial_number: Mapped[str] = mapped_column(String(100), unique=True)
    model: Mapped[str] = mapped_column(String(100))
    status: Mapped[EquipmentStatus] = mapped_column(
        SqlEnum(EquipmentStatus, name="equipment_status", values_callable=lambda x: [m.value for m in x]),
        default=EquipmentStatus.AVAILABLE,
    )
    charge_level: Mapped[int] = mapped_column(Numeric(5, 2))
    facility_id: Mapped[int] = mapped_column(Integer, ForeignKey("hospitals.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    hospital: Mapped["Hospital"] = relationship(back_populates="equipments")
    work_order: Mapped["WorkOrder"] = relationship(back_populates="equipment")
    
    
        
        
        
        



"""
+------------------+         +------------------+         +------------------+
|     Hospital     | 1 --- * |     Equipment    | 1 --- * |    Work Order    |
+------------------+         +------------------+         +------------------+
| id               |         | id               |         | id               |
| name             |         | serial_number    |         | title            |
| location_region  |         | model            |         | priority         |
| capacity         |         | status           |         | status           |
| supervisor_id    |         | charge_level     |         | equipment_id     |
+------------------+         | facility_id      |         | technician_id    |
                             +------------------+         +------------------+
                               """
