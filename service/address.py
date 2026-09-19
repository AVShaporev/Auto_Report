"""Сборка человекочитаемого адреса объекта / организации (как в актах).

Формат: «<регион> <тип>, <район> <тип>, <тип.> <нас. пункт>, <тип.> <улица>,
<д.> N, <пом.> N». Тип берётся из справочников spec_*: у региона/района —
полное имя после названия («Московская область»), у нас. пункта/улицы —
сокращение перед названием («г. Химки», «ул. Ленина»).

Защита от дублей (2026-09-19, демо-стенд: «г. Москва Город, …, ул. ул. Тверская»):
  - тип не добавляется, если название уже с ним («ул. Тверская», «Тверская
    улица») или начинается со своего сокращения («г. Москва» при типе
    «Город») — пользователи часто вводят название вместе с типом;
  - одинаковые части подряд не повторяются (Москва — и регион, и город).
"""
import re
from typing import Any, Iterable, Optional

# Название уже начинается со своего сокращения типа: «г. Москва», «пос. Ильинский»,
# «ул. Тверская», «обл. …» — строчные буквы + точка. У типов регионов/районов
# нет short_name, поэтому «г. Москва» + «Город» иначе не распознать.
_OWN_ABBR_PREFIX = re.compile(r'^[а-яё][а-яё-]{0,5}\.\s*\S')


def _clean(value: Any) -> str:
    return str(value).strip() if value else ''


def _has_type(name: str, type_names: Iterable[Optional[str]]) -> bool:
    """Название уже содержит тип в начале или в конце (без учёта регистра/точки)."""
    if _OWN_ABBR_PREFIX.match(name.strip()):
        return True
    n = ' '.join(name.casefold().split())
    for t in type_names:
        t = _clean(t).casefold()
        base = t.rstrip('.').strip()
        if not base:
            continue
        if n == base or n == t:
            return True
        if n.startswith(base + ' ') or n.startswith(base + '.'):
            return True
        if n.endswith(' ' + base) or n.endswith(' ' + t):
            return True
    return False


def _with_suffix(name: str, spec: Any) -> str:
    """«Московская» + «область» → «Московская область» (если тип ещё не в названии)."""
    type_name = _clean(getattr(spec, 'name', None)) if spec else ''
    types = [type_name, getattr(spec, 'short_name', None) if spec else None]
    if type_name and not _has_type(name, types):
        return f'{name} {type_name}'
    return name


def _with_prefix(name: str, spec: Any) -> str:
    """«г.» + «Химки» → «г. Химки» (если тип ещё не в названии)."""
    short = _clean(getattr(spec, 'short_name', None)) if spec else ''
    types = [short, getattr(spec, 'name', None) if spec else None]
    if short and not _has_type(name, types):
        return f'{short} {name}'
    return name


def address_parts(entity: Any, *, room_default: str = 'пом.', use_spec_room: bool = True) -> list[str]:
    """Части адреса Object/Organization (одинаковый набор полей и связей)."""
    parts: list[str] = []

    def add(part: str) -> None:
        part = part.strip()
        if part and all(part.casefold() != p.casefold() for p in parts):
            parts.append(part)

    region = getattr(entity, 'region', None)
    if region and _clean(region.name):
        add(_with_suffix(_clean(region.name), getattr(region, 'spec_region', None)))
    arial = getattr(entity, 'arial', None)
    if arial and _clean(arial.name):
        add(_with_suffix(_clean(arial.name), getattr(arial, 'spec_arial', None)))
    locality = getattr(entity, 'locality', None)
    if locality and _clean(locality.name):
        add(_with_prefix(_clean(locality.name), getattr(locality, 'spec_locality', None)))
    street = getattr(entity, 'street', None)
    if street and _clean(street.name):
        add(_with_prefix(_clean(street.name), getattr(street, 'spec_street', None)))

    build_number = _clean(getattr(entity, 'build_number', None))
    if build_number:
        spec_build = getattr(entity, 'spec_build', None)
        prefix = _clean(getattr(spec_build, 'name', None)) or 'д.'
        add(build_number if _has_type(build_number, [prefix]) else f'{prefix} {build_number}')
    room_number = _clean(getattr(entity, 'room_number', None))
    if room_number:
        spec_room = getattr(entity, 'spec_room', None) if use_spec_room else None
        prefix = _clean(getattr(spec_room, 'name', None)) or room_default
        add(room_number if _has_type(room_number, [prefix]) else f'{prefix} {room_number}')
    return parts
