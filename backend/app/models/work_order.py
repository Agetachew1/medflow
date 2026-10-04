
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, ForeignKey
from .base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .enums import WorkOrderPriority, WorkOrderStatus
from sqlalchemy import Enum as SqlEnum


if TYPE_CHECKING:
    from .equipment import Equipment
    from .technician import Technician
    from .service_report import ServiceReport
    from .user import User


class WorkOrder(Base):
    __tablename__ = "work_orders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title:Mapped[str] = mapped_column(String(100))
    priority: Mapped[WorkOrderPriority] = mapped_column(
        SqlEnum(
            WorkOrderPriority,
            name= "work_order_priority",
            values_callable = lambda enum_cls: [member.value for member in enum_cls],
        )
    )
    status: Mapped[WorkOrderStatus] = mapped_column(
        SqlEnum(
            WorkOrderStatus,
            name= "work_order_Status",
            values_callable = lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=WorkOrderStatus.PENDING
    )
    equipment_id: Mapped[int] = mapped_column(Integer, ForeignKey("equipments.id"))
    technician_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    
    equipment: Mapped["Equipment"] = relationship(back_populates="work_order")
    
    technician: Mapped["User"] = relationship("User")
    service_report: Mapped[list["ServiceReport"]] = relationship(back_populates="work_order")
    
    def mark_completed(self) -> None:
        self.status = WorkOrderStatus.COMPLETED
    
    def mark_failed(self) -> None:
        self.status = WorkOrderStatus.FAILED
        
    def __repr__(self) -> str:
        return f"WorkOrder(id={self.id}, title={self.title!r}, priority={self.priority.value}, status={self.status.value})"

