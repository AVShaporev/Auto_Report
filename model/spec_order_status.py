from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base, int_pk, str_uniq


# Справочник статусов заявки на ТО.
#
# Order.status на модели — plain str (без FK), исторически. Эта таблица
# существует чтобы дать веб- и мобильному фронту единый источник ру-имён
# статусов (плюс порядок в селектах). Связь soft: Order.status = code
# из этой таблицы (JOIN'ится в data-слое, см. data/mobile.py).
#
# Валидация «код должен быть из этой таблицы» — на уровне API-схемы
# (Literal[...] в api/order.py update_order_status), не на уровне FK.
# Это осознанно: чтобы миграция была чисто аддитивной и обратимой.
class Spec_Order_Status(Base):

    id: Mapped[int_pk]
    name: Mapped[str_uniq]   # 'Новая', 'В работе', 'Выполнена', 'Отменена'
    code: Mapped[str_uniq]   # 'new', 'in_progress', 'completed', 'cancelled'
    is_system: Mapped[bool] = mapped_column(default=False, server_default='false')
    display_order: Mapped[int] = mapped_column(default=0, server_default='0')

    def __str__(self):
        return f"Spec_Order_Status(id={self.id}, code={self.code})"

    def __repr__(self):
        return str(self)
