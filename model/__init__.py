"""
Регистрирует все SQLAlchemy-модели в Base.metadata через side-effect импортов.

Импортируется любым кодом, которому нужно «увидеть» все таблицы:
- alembic-миграции
- служебные скрипты (bootstrap_admin.py)
- любой код, обращающийся к моделям без захода через api/service.

Боевое приложение тянет всё через цепочку импортов api → service → data → model,
но для standalone-скриптов этой цепочки нет — поэтому держим список здесь.
"""

from database.database import Base

# Справочники (spec_*)
from model.spec_arial import Spec_Arial
from model.spec_build import Spec_Build
from model.spec_contract import Spec_Contract
from model.spec_equipment import Spec_Equipment
from model.spec_job_title import Spec_Job_Title
from model.spec_locality import Spec_Locality
from model.spec_order import Spec_Order
from model.spec_order_status import Spec_Order_Status
from model.spec_priority import Spec_Priority
from model.spec_region import Spec_Region
from model.spec_report_status import Spec_Report_Status
from model.spec_room import Spec_Room
from model.spec_status import Spec_Status
from model.spec_street import Spec_Street
from model.spec_system import Spec_System

# Базовые сущности
from model.bank import Bank
from model.region import Region
from model.arial import Arial
from model.locality import Locality
from model.street import Street
from model.period import Period
from model.organization import Organization

# Бизнес-сущности (зависят от справочников / базовых)
from model.role import Role
from model.user import User
from model.user_session import UserSession
from model.push_token import PushToken
from model.idempotency_key import IdempotencyKey
from model.media_upload_session import MediaUploadSession
from model.contract import Contract
from model.sub_contract import Sub_Contract
from model.object import Object
from model.equipment import Equipment
from model.objects_equipment import Objects_Equipment
from model.operation import Operation  # содержит Table operations_spec_equipments
from model.order import Order
from model.issue import Issue
from model.report import Report
from model.report_attachment import Report_Attachment
from model.issue_attachment import Issue_Attachment


__all__ = [
    "Base",
    # spec_*
    "Spec_Arial", "Spec_Build", "Spec_Contract", "Spec_Equipment",
    "Spec_Job_Title", "Spec_Locality", "Spec_Order", "Spec_Order_Status",
    "Spec_Priority",
    "Spec_Region", "Spec_Report_Status",
    "Spec_Room", "Spec_Status", "Spec_Street", "Spec_System",
    # базовые
    "Bank", "Region", "Arial", "Locality", "Street", "Period", "Organization",
    # бизнес
    "Role", "User", "UserSession", "PushToken", "IdempotencyKey",
    "MediaUploadSession",
    "Contract", "Sub_Contract",
    "Object", "Equipment", "Objects_Equipment",
    "Operation",
    "Order", "Issue", "Report",
    "Report_Attachment", "Issue_Attachment",
]
