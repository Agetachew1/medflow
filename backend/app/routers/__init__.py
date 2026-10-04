from backend.app.routers.auth import router as auth_router
from .equipment import router as equipment_router
from .work_orders import router as work_order_router
from .hospitals import router as hospital_router
from .service_reports import router as service_report_router
from .users import router as users_router

__all__ = [
    "auth_router",
    "equipment_router",
    "work_order_router",
    "hospital_router",
    "service_report_router",
    "users_router"
]