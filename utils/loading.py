"""SQLAlchemy-загрузочные хелперы для борьбы с N+1.

Модели в проекте активно используют `lazy="selectin"`/`lazy="joined"` на
коллекциях/M:1 связях. При выдаче списков (Order, Report, Contract …) это
порождает каскад: загрузили N контрактов → каждый сам тянет customer/executor
(joined), spec_contract/reports/orders (selectin) → каждый объект тянет 11
свои eager-relation и т. д. — отсюда 300+ SQL-запросов на один эндпоинт.

`shallow_load(rel)` решает это узко: грузит `rel` (отдельным batched SELECT),
но для дальнейших связей у загруженного объекта ставит `raiseload("*")` —
любое случайное обращение к ним падает явной ошибкой (а не молча тянет
ещё одну гирлянду SELECT'ов).
"""

from sqlalchemy.orm import selectinload, raiseload


def shallow_load(*relations):
    """Селективно загрузить relations и отрубить второй уровень автозагрузок.

    Пример: для `Order` нужно только название spec_order, номер contract,
    name объекта и юзера. Без вложенностей:

        query.options(
            *shallow_load(
                Order.spec_order, Order.contract, Order.object, Order.user
            ),
            raiseload(Order.report),  # обрубить «фантомные» auto-selectin
        )
    """
    return [selectinload(rel).raiseload("*") for rel in relations]
