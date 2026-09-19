"""build_address / _build_org_address — формат адреса и защита от дублей типа.

Чистые функции, без БД (объекты — SimpleNamespace с теми же полями, что у
Object/Organization). Случай из демо 2026-09-19: «г. Москва Город, …, ул. ул. Тверская».
"""
from types import SimpleNamespace as N

import pytest

from service.render_docx import build_address, _build_org_address


def _obj(region=None, sr=None, arial=None, sa=None, loc=None, sl_short=None,
         street=None, ss_short=None, build=None, sb=None, room=None, sroom=None, postal=None):
    return N(
        region=N(name=region, spec_region=N(name=sr) if sr else None) if region else None,
        arial=N(name=arial, spec_arial=N(name=sa) if sa else None) if arial else None,
        locality=N(name=loc, spec_locality=N(name='Город', short_name=sl_short)) if loc else None,
        street=N(name=street, spec_street=N(name='Улица', short_name=ss_short)) if street else None,
        build_number=build, spec_build=N(name=sb) if sb else None,
        room_number=room, spec_room=N(name=sroom) if sroom else None,
        postal_code=postal,
    )


@pytest.mark.parametrize('obj, expected', [
    (_obj('г. Москва', 'Город', 'ЦАО', 'Административный округ', 'г. Москва', 'г.', 'ул. Тверская', 'ул.', '5'),
     'г. Москва, ЦАО Административный округ, ул. Тверская, д. 5'),
    (_obj('Московская', 'область', 'Одинцовский', 'район', 'Одинцово', 'г.', 'Ленина', 'ул.', '12', 'корп.', '3', 'оф.'),
     'Московская область, Одинцовский район, г. Одинцово, ул. Ленина, корп. 12, оф. 3'),
    (_obj(loc='Химки', sl_short='г.', street='Тверская улица', ss_short='ул.'), 'г. Химки, Тверская улица'),
    (_obj(loc='Гатчина', sl_short='г.'), 'г. Гатчина'),
    (_obj(street='Ленина', ss_short='ул.', build='д. 7'), 'ул. Ленина, д. 7'),
    (_obj(), '—'),
])
def test_build_address(obj, expected):
    assert build_address(obj) == expected


def test_build_org_address_postal_and_room():
    org = _obj('Московская', 'область', loc='Химки', sl_short='г.', street='ул. Мира', ss_short='ул.',
               build='1', room='2', sroom='оф.', postal='141400')
    assert _build_org_address(org) == '141400, Московская область, г. Химки, ул. Мира, д. 1, пом. 2'
