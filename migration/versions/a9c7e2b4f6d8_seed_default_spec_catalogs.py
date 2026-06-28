"""seed default spec_* catalogs for new tenants

Идемпотентный seed системных строк в 8 справочниках:
  - spec_streets       — типы улиц (РФ ФИАС-сокращения)
  - spec_localitys     — типы населённых пунктов
  - spec_arials        — типы районов
  - spec_builds        — типы строений
  - spec_rooms         — типы помещений
  - spec_contracts     — типы договоров
  - spec_job_titles    — должности
  - spec_systems       — обслуживаемые системы (с разделением fire / нет)
  - spec_equipments    — типы оборудования (взяты из hi-tech как эталона)

Зачем: новый provisioned-tenant (SaaS) сейчас получает пустые spec_* →
клиент перед первым объектом должен сам набивать «улицы / переулки», «г. /
с. / д.» и т.п. Эта миграция засеивает универсальный РФ-набор, который
применим почти любому клиенту. После накатывания каждая строка помечается
`is_system=TRUE` и в UI отображается с бейджем + защитой от удаления
(Phase A/B system rows).

Идемпотентность (та же стратегия, что в c3a7f2b9e814 / f5d8a2c1e9b4):
  1. INSERT ... ON CONFLICT (name) DO NOTHING — если строка с таким
     name уже есть, не дублируем.
  2. UPDATE SET is_system = TRUE WHERE name IN (...) — промаркируем
     уже существующие строки (типичный кейс: hi-tech, где справочники
     были заведены до Phase A).

Не сидим:
  - spec_regions / regions / arials / streets / localitys — основные
    географические таблицы. Это Этап 9.6-B (КЛАДР/ФИАС-импорт).
  - spec_statuss / spec_prioritys / spec_orders / spec_journals — уже
    сидятся отдельными миграциями (c3a7f2b9e814, f5d8a2c1e9b4,
    b8e2f4a6d5c3). Здесь не дублируем.

Revision ID: a9c7e2b4f6d8
Revises: e7c2a5d1f3b8
Create Date: 2026-06-28
"""
from alembic import op
import sqlalchemy as sa


revision = 'a9c7e2b4f6d8'
down_revision = 'e7c2a5d1f3b8'
branch_labels = None
depends_on = None


# ============================================================================
# Данные для seed'а
# ============================================================================

SPEC_STREETS = [
    # (name, short_name)
    ('улица',      'ул.'),
    ('переулок',   'пер.'),
    ('проспект',   'просп.'),
    ('бульвар',    'б-р'),
    ('шоссе',      'ш.'),
    ('набережная', 'наб.'),
    ('площадь',    'пл.'),
    ('тупик',      'туп.'),
    ('проезд',     'пр-д'),
    ('аллея',      'ал.'),
    ('тракт',      'тр-т'),
    ('микрорайон', 'мкр.'),
    ('квартал',    'кв-л'),
    ('линия',      'лин.'),
    ('съезд',      'сз.'),
]

SPEC_LOCALITYS = [
    # (name, short_name)
    ('город',                                              'г.'),
    ('посёлок городского типа',                            'пгт.'),
    ('посёлок',                                            'п.'),
    ('село',                                               'с.'),
    ('деревня',                                            'д.'),
    ('станица',                                            'ст-ца'),
    ('хутор',                                              'х.'),
    ('рабочий посёлок',                                    'рп.'),
    ('садоводческое некоммерческое товарищество',          'СНТ'),
]

SPEC_ARIALS = [
    'городской район',
    'административный округ',
    'муниципальный район',
    'городской округ',
    'внутригородская территория',
]

SPEC_BUILDS = [
    # ФИАС-типы строений в адресе («ул. Тверская, д. 1, стр. 2, корп. А»).
    'дом',
    'строение',
    'корпус',
    'владение',
    'сооружение',
    'литера',
    'участок',
    'здание',
]

SPEC_ROOMS = [
    # ФИАС-типы помещений в адресе («... пом. 5», «... оф. 12», «... кв. 47»).
    'квартира',
    'помещение',
    'офис',
    'комната',
    'кабинет',
    'бокс',
    'павильон',
    'машино-место',
]

SPEC_CONTRACTS = [
    'Договор',
    'Контракт',
    'Государственный контракт',
    'Муниципальный контракт',
    'Договор подряда',
    'Договор поставки',
    'Договор сервисного обслуживания',
    'Соглашение',
]

SPEC_JOB_TITLES = [
    'Генеральный директор',
    'Директор',
    'Технический директор',
    'Главный инженер',
    'Заместитель директора',
    'Управляющий',
    'Председатель правления',
    'Индивидуальный предприниматель',
]

# (name, short_name, is_fire_protection)
SPEC_SYSTEMS = [
    ('Автоматическая пожарная сигнализация',                'АПС',     True),
    ('Система оповещения и управления эвакуацией',          'СОУЭ',    True),
    ('Автоматические установки пожаротушения',              'АУПТ',    True),
    ('Внутренний противопожарный водопровод',               'ВПВ',     True),
    ('Система противодымной защиты',                        'СПДЗ',    True),
    ('Автоматический дымоудалитель',                        'АДУ',     True),
    ('Видеонаблюдение',                                     'CCTV',    False),
    ('Система контроля и управления доступом',              'СКУД',    False),
    ('Электроснабжение',                                    'ЭС',      False),
]

# Базовый набор spec_equipments взят из hi-tech как эталонного донора.
# Универсальная номенклатура (пожарка + охранка + видеонаблюдение),
# которая применима практически любому клиенту в нашем сегменте.
SPEC_EQUIPMENTS = [
    'Видеорегистратор до 16 каналов',
    'Внешняя видеокамера',
    'Внутренняя видеокамера',
    'Вспомогательное оборудование',
    'Модуль газового пожаротушения',
    'Модуль порошкового пожаротушения',
    'Огнетушитель',
    'Оповещатель',
    'Охранный извещатель',
    'Пожарный извещатель',
    'Пожарный кран',
    'Пожарный оповещатель',
    'Прибор приемно-контрольный или прибор пожарный управления',
    'Промежуточное устройство управления и контроля',
    'Система охранно-пожарной сигнализации',
]


# ============================================================================
# Хелперы
# ============================================================================

def _seed_simple(conn, table: str, names: list[str]) -> None:
    """INSERT ON CONFLICT (name) DO NOTHING + UPDATE is_system=TRUE.

    Для справочников с единственным полем `name` + is_system.
    """
    for name in names:
        conn.execute(
            sa.text(
                f"INSERT INTO {table} (name, is_system) "
                f"VALUES (:name, TRUE) "
                f"ON CONFLICT (name) DO NOTHING"
            ),
            {"name": name},
        )
        conn.execute(
            sa.text(
                f"UPDATE {table} SET is_system = TRUE WHERE name = :name"
            ),
            {"name": name},
        )


def _seed_with_short(conn, table: str, rows: list[tuple]) -> None:
    """То же, но для таблиц с парой (name, short_name)."""
    for name, short_name in rows:
        conn.execute(
            sa.text(
                f"INSERT INTO {table} (name, short_name, is_system) "
                f"VALUES (:name, :short_name, TRUE) "
                f"ON CONFLICT (name) DO NOTHING"
            ),
            {"name": name, "short_name": short_name},
        )
        conn.execute(
            sa.text(
                f"UPDATE {table} SET is_system = TRUE WHERE name = :name"
            ),
            {"name": name},
        )


def _seed_systems(conn) -> None:
    """spec_systems = name, short_name, is_fire_protection, is_system."""
    for name, short_name, is_fire in SPEC_SYSTEMS:
        conn.execute(
            sa.text(
                "INSERT INTO spec_systems (name, short_name, is_fire_protection, is_system) "
                "VALUES (:name, :short_name, :is_fire, TRUE) "
                "ON CONFLICT (name) DO NOTHING"
            ),
            {"name": name, "short_name": short_name, "is_fire": is_fire},
        )
        # На существующих строках только промаркируем is_system;
        # is_fire_protection НЕ трогаем — могло быть выставлено вручную.
        conn.execute(
            sa.text(
                "UPDATE spec_systems SET is_system = TRUE WHERE name = :name"
            ),
            {"name": name},
        )


# ============================================================================
# upgrade / downgrade
# ============================================================================

def upgrade() -> None:
    conn = op.get_bind()

    _seed_with_short(conn, 'spec_streets',   SPEC_STREETS)
    _seed_with_short(conn, 'spec_localitys', SPEC_LOCALITYS)

    _seed_simple(conn, 'spec_arials',     SPEC_ARIALS)
    _seed_simple(conn, 'spec_builds',     SPEC_BUILDS)
    _seed_simple(conn, 'spec_rooms',      SPEC_ROOMS)
    _seed_simple(conn, 'spec_contracts',  SPEC_CONTRACTS)
    _seed_simple(conn, 'spec_job_titles', SPEC_JOB_TITLES)
    _seed_simple(conn, 'spec_equipments', SPEC_EQUIPMENTS)

    _seed_systems(conn)


def downgrade() -> None:
    # Заведённые строки могут уже быть привязаны FK (street.spec_street_id,
    # object.spec_build_id и т.п.) — безопасный downgrade невозможен.
    # Просто снимаем флаг is_system, чтобы строки стали «обычными» с точки
    # зрения UI; удалять их пусть юзер сам решает.
    conn = op.get_bind()

    def unflag(table: str, names: list[str]) -> None:
        if not names:
            return
        conn.execute(
            sa.text(
                f"UPDATE {table} SET is_system = FALSE "
                f"WHERE name = ANY(:names)"
            ),
            {"names": names},
        )

    unflag('spec_streets',   [n for n, _ in SPEC_STREETS])
    unflag('spec_localitys', [n for n, _ in SPEC_LOCALITYS])
    unflag('spec_arials',    SPEC_ARIALS)
    unflag('spec_builds',    SPEC_BUILDS)
    unflag('spec_rooms',     SPEC_ROOMS)
    unflag('spec_contracts', SPEC_CONTRACTS)
    unflag('spec_job_titles', SPEC_JOB_TITLES)
    unflag('spec_equipments', SPEC_EQUIPMENTS)
    unflag('spec_systems',   [n for n, _, _ in SPEC_SYSTEMS])
