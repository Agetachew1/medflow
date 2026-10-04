from __future__ import annotations
from sqlalchemy import ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SqlEnum

from .base import Base
from typing import TYPE_CHECKING
from .enums import UserRole

# Move the import down here!
if TYPE_CHECKING:
    from .hospital import Hospital

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_cls: [member.value for member in enum_cls]
        )
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    hospital_id: Mapped[int | None] = mapped_column(ForeignKey("hospitals.id"), nullable=True)
    hospital: Mapped["Hospital"] = relationship("Hospital", back_populates="users")
    
    def __repr__(self) -> str:
        return f"User(id={self.id}, username={self.username!r}, role={self.role.value}, hospital_id={self.hospital_id})"