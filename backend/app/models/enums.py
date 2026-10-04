from enum import Enum 

class EquipmentStatus(str, Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    UNDER_MAINTENANCE = "under_maintenance"
    OFFLINE = "offline"
    
class WorkOrderStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class WorkOrderPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    CRITICAL = "critical"
    
class UserRole(str, Enum):
    CLINICAL_ADMIN = "clinical_admin"
    FIELD_TECHNICIAN = "field_technician"
    HOSPITAL_MANAGER = "hospital_manager"
