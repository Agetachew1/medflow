
from sqlalchemy import String, Integer, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .hospital import Hospital
    from .work_order import WorkOrder

class Technician(Base):
    __tablename__ = "technician"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    