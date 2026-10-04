from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Integer, DATE, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship



from .base import Base
if TYPE_CHECKING:
    from .work_order import WorkOrder

class ServiceReport(Base):
    __tablename__ = "service_reports"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_order_id: Mapped[int] = mapped_column(Integer, ForeignKey("work_orders.id"))
    file_url: Mapped[str] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    work_order: Mapped["WorkOrder"] = relationship("WorkOrder")
    
    def __repr__(self) -> str:
        return f"ServiceReport(id={self.id}, work_order_id={self.work_order_id!r})"





"""
|  Service Report  |
+------------------+
| id               |
| file_url (S3)    |
| notes            |
| timestamp        |
+------------------+"""
