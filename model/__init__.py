"""
Инициализация всех моделей SQLAlchemy
Этот файл гарантирует, что все модели зарегистрированы в правильном порядке
"""

# Сначала импортируем Base
from database.database import Base

# Затем импортируем все модели в правильном порядке
# Сначала независимые модели (без внешних ключей)
from model.region import Region
from model.arial import Arial
from model.locality import Locality
from model.street import Street
from model.spec_build import Spec_Build
from model.spec_room import Spec_Room
from model.spec_equipment import Spec_Equipment
from model.spec_contract import Spec_Contract
from model.spec_job_title import Spec_Job_Title
from model.spec_order import Spec_Order
from model.spec_region import Spec_Region
from model.objects_equipment import Objects_Equipment
from model.bank import Bank
from model.spec_job_title import Spec_Job_Title
from model.spec_arial import Spec_Arial
from model.spec_locality import Spec_Locality
from model.spec_street import Spec_Street
from model.spec_build import Spec_Build
from model.spec_room import Spec_Room

# Затем модели, зависящие от других
from model.equipment import Equipment  # Зависит от Spec_Equipment
from model.contract import Contract
from model.period import Period
from model.object import Object
from model.order import Order
from model.report import Report
from model.user import User
from model.role import Role
from model.region import Region
from model.organization import Organization
from model.region import Region
from model.arial import Arial
from model.locality import Locality
from model.street import Street

# Экспортируем все модели для удобства
__all__ = [
    'Base',
    'Region', 'Arial', 'Locality', 'Street',
    'Spec_Build', 'Spec_Room', 'Spec_Equipment', 'Spec_Contract', 
    'Spec_Job_Title', 'Spec_Order', 'Spec_Region', 'Spec_Arial',
    'Bank', 'Equipment', 'Contract', 'Period', 'Object',
    'Order', 'Report', 'User', 'Role', 'Organization',
    'Spec_Job_Title', 'Arial' 
]