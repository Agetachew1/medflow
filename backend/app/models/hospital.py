from __future__ import annotations
from typing import TYPE_CHECKING, List
from sqlalchemy import Integer, String
# DELETE the User import from here
from .base import Base   # (Also changed this to a clean relative import)
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .equipment import Equipment
    from .user import User   # Add it down here!
    
class Hospital(Base):
    __tablename__ = "hospitals"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    location_region: Mapped[str] = mapped_column(String(100), index=True)
    capacity: Mapped[int] = mapped_column(Integer)
    supervisor_id: Mapped[int] = mapped_column(Integer, index=True)
    
    equipments: Mapped[List[Equipment]] = relationship("Equipment", back_populates="hospital")
    users: Mapped[List["User"]] = relationship("User", back_populates="hospital")
    
    def __repr__(self) -> str:
        return f"Hospital(id={self.id}, name={self.name}, location_region={self.location_region}, capacity={self.capacity})"
