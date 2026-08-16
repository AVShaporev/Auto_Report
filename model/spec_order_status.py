from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base, int_pk, str_uniq


# Справочник статусов заявки на ТО. Канон 4 поля (миграция a0b1c2d3e4f5):
#   id, name, description (из Base), is_default.
#
# Order.status_id — FK на эту таблицу. API везде оперирует id + name
# (name — ру-имя для отображения); code, is_system, display_order убраны.
#
# is_default = true — статус по умолчанию для новых заявок (используется
# autogen'ом и create_order когда клиент явно status_id не передал).
# Partial unique index на (is_default) WHERE is_default = true гарантирует
# ровно одну дефолтную строку.
class Spec_Order_Status(Base):
    __tablename__ = 'spec_order_statuses'

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    is_default: Mapped[bool] = mapped_column(default=False, server_default='false')

    def __str__(self):
        return f"Spec_Order_Status(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)
