from sqlalchemy.orm import Mapped, mapped_column

from database.database import Base, int_pk, str_uniq


# Справочник статусов отчёта. Канон 4 поля (миграция f3a4b5c6d7e8):
#   id, name, description (из Base), is_default.
#
# Report.status_id — FK на эту таблицу (было spec_statuss). API/фронт
# оперируют id + name.
#
# is_default = true — статус по умолчанию для новых отчётов («В работе»).
# Partial unique index на (is_default) WHERE is_default = true гарантирует
# ровно одну дефолтную строку.
class Spec_Report_Status(Base):
    __tablename__ = 'spec_report_statuses'

    id: Mapped[int_pk]
    name: Mapped[str_uniq]
    is_default: Mapped[bool] = mapped_column(default=False, server_default='false')

    def __str__(self):
        return f"Spec_Report_Status(id={self.id}, name={self.name})"

    def __repr__(self):
        return str(self)
