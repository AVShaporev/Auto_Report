"""
scripts/generate_demo_templates.py — генератор 4 демо-шаблонов для
demo-тенанта cool-doc.ru через python-docx.

Зачем отдельный скрипт:
- Файлы в `templates/seeds/*.docx` изначально были плейсхолдерами
  (без docxtpl-разметки). Для демо нужно, чтобы кнопка «Скачать акт»
  сразу показывала работу подстановки данных из БД.
- Ручное редактирование Word'а под docxtpl-разметку хрупко (Word
  разбивает `{{ name }}` на несколько runs). Проще собрать шаблон
  программно через python-docx — каждый плейсхолдер один run.

Что генерируется:
- planned.dotx        — Акт планового ТО с таблицей оборудования
                        через {%tr for group in equipment_groups %}
- maintenance.docx    — Акт технического обслуживания (упрощённая
                        версия planned)
- emergency.docx      — Акт по аварийной заявке (без таблицы
                        оборудования, с описанием проблемы)
- primary.dotx        — Акт первичного осмотра (адрес, ответственный,
                        таблица оборудования)
- journal_maint.docx  — Журнал технического обслуживания объекта
                        (контекст журнала: без order.*, только object,
                        contract, customer, executor, today*)
- journal_primary.docx — Журнал первичного осмотра объекта

Контекст docxtpl (см. `service/render_docx.py::_build_context`):
    order.number, order.created_at, order.description
    contract.number, contract.date_of_consclusion,
        contract.date_of_completion, contract.subject,
        contract.short_subject, contract.spec_contract.name
    customer.name, customer.short_name, customer.inn, customer.kpp,
        customer.director_full_name, customer.address
    executor.<то же>
    object.name, object.address, object.responsible_face,
        object.responsible_faces_contact
    user.full_name, user.role_name
    today, today_long
    equipment_groups: [{index, system_name, rows: [{index, name, count}]}]
    qr (InlineImage — не используется в этих семплах)

Запуск:
    python scripts/generate_demo_templates.py

Перезаписывает файлы в templates/seeds/. Коммитить как обычно.
"""

from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / 'templates' / 'seeds'


# ---------------------------------------------------------------------------
# Утилиты форматирования
# ---------------------------------------------------------------------------


def _set_default_font(doc: Document) -> None:
    """Times New Roman 12pt как базовый шрифт документа — привычно
    для формальных актов."""
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(12)
    # Восточно-Азиатский fallback — чтобы Word не подставлял свой
    style.element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')


def _add_title(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(14)


def _add_paragraph(doc: Document, text: str, bold: bool = False,
                   align: WD_ALIGN_PARAGRAPH = WD_ALIGN_PARAGRAPH.LEFT) -> None:
    p = doc.add_paragraph()
    p.alignment = align
    run = p.add_run(text)
    run.bold = bold


def _add_kv_row(doc: Document, label: str, jinja: str) -> None:
    """Строка «Метка: {{ jinja.expression }}»."""
    p = doc.add_paragraph()
    r1 = p.add_run(f'{label}: ')
    r1.bold = True
    p.add_run(jinja)


def _add_signatures(doc: Document) -> None:
    """Две подписи снизу — заказчик и исполнитель, с ФИО директоров."""
    doc.add_paragraph()  # отступ
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    table.columns[0].width = Cm(8)
    table.columns[1].width = Cm(8)

    left, right = table.rows[0].cells
    left.paragraphs[0].add_run('Заказчик:').bold = True
    left.add_paragraph('{{ customer.director_full_name }}')
    left.add_paragraph('_________________ / М.П.')
    left.add_paragraph('«____» ____________ 20__ г.')

    right.paragraphs[0].add_run('Исполнитель:').bold = True
    right.add_paragraph('{{ executor.director_full_name }}')
    right.add_paragraph('_________________ / М.П.')
    right.add_paragraph('«____» ____________ 20__ г.')


def _add_equipment_table(doc: Document) -> None:
    """Таблица оборудования через nested {%tr for %} — 2 уровня
    (раздел = система, строки = единицы).

    docxtpl-семантика: строка таблицы с `{%tr … %}` целиком удаляется
    после парсинга. Значит для nested-цикла нужно 6 строк:
      1. header (№ / Наименование / Кол-во) — остаётся
      2. `{%tr for group in equipment_groups %}` — удаляется
      3. группа: `1. {{ group.system_name }}` — остаётся, N раз
      4. `{%tr for row in group.rows %}` — удаляется
      5. элемент: `1.1 | {{ row.name }} | {{ row.count }}` — остаётся, K раз
      6. `{%tr endfor %}` (закрытие row) — удаляется
      7. `{%tr endfor %}` (закрытие group) — удаляется
    """
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Table Grid'
    table.autofit = False
    table.columns[0].width = Cm(2)
    table.columns[1].width = Cm(11)
    table.columns[2].width = Cm(3)

    # (1) header
    hdr = table.rows[0].cells
    for cell, text in zip(hdr, ('№', 'Наименование системы / оборудования', 'Кол-во')):
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = cell.paragraphs[0].add_run(text)
        run.bold = True

    # (2) открытие внешнего цикла — вся строка будет удалена docxtpl
    open_outer = table.add_row().cells
    open_outer[0].paragraphs[0].add_run('{%tr for group in equipment_groups %}')

    # (3) отрисовка группы: №, название системы
    group_row = table.add_row().cells
    group_row[0].paragraphs[0].add_run('{{ group.index }}.')
    group_row[1].paragraphs[0].add_run('{{ group.system_name }}').bold = True
    group_row[2].paragraphs[0].add_run('')

    # (4) открытие внутреннего цикла
    open_inner = table.add_row().cells
    open_inner[0].paragraphs[0].add_run('{%tr for row in group.rows %}')

    # (5) отрисовка элемента: индекс.подиндекс, название, количество
    item_row = table.add_row().cells
    item_row[0].paragraphs[0].add_run('{{ row.index }}')
    item_row[1].paragraphs[0].add_run('{{ row.name }}')
    item_row[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    item_row[2].paragraphs[0].add_run('{{ row.count }}')

    # (6) закрытие внутреннего цикла
    close_inner = table.add_row().cells
    close_inner[0].paragraphs[0].add_run('{%tr endfor %}')

    # (7) закрытие внешнего цикла
    close_outer = table.add_row().cells
    close_outer[0].paragraphs[0].add_run('{%tr endfor %}')

    # Немного дыхания под таблицей
    doc.add_paragraph()


# ---------------------------------------------------------------------------
# 1. Плановое ТО (planned.dotx)
# ---------------------------------------------------------------------------


def gen_planned() -> Path:
    doc = Document()
    _set_default_font(doc)

    _add_title(doc, 'АКТ № {{ order.number }}')
    _add_paragraph(doc, 'выполненных работ по плановому техническому обслуживанию',
                   align=WD_ALIGN_PARAGRAPH.CENTER)
    _add_paragraph(doc, 'по договору № {{ contract.number }} от {{ contract.date_of_consclusion }} г.',
                   align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()

    _add_kv_row(doc, 'г. Москва', '{{ today_long }}')
    doc.add_paragraph()

    _add_paragraph(doc, 'Стороны:', bold=True)
    _add_kv_row(doc, 'Заказчик', '{{ customer.name }}, ИНН {{ customer.inn }}, КПП {{ customer.kpp }}')
    _add_kv_row(doc, 'Адрес заказчика', '{{ customer.address }}')
    _add_kv_row(doc, 'Исполнитель', '{{ executor.name }}, ИНН {{ executor.inn }}, КПП {{ executor.kpp }}')
    _add_kv_row(doc, 'Адрес исполнителя', '{{ executor.address }}')
    doc.add_paragraph()

    _add_paragraph(doc, 'Объект обслуживания:', bold=True)
    _add_kv_row(doc, 'Наименование', '{{ object.name }}')
    _add_kv_row(doc, 'Адрес', '{{ object.address }}')
    _add_kv_row(doc, 'Ответственный на объекте', '{{ object.responsible_face }}')
    _add_kv_row(doc, 'Контакт', '{{ object.responsible_faces_contact }}')
    doc.add_paragraph()

    _add_paragraph(doc, 'Выполненные работы по обслуживанию оборудования:', bold=True)
    _add_equipment_table(doc)

    _add_paragraph(doc, 'Комментарий по заявке:', bold=True)
    _add_paragraph(doc, '{{ order.description }}')
    doc.add_paragraph()

    _add_paragraph(doc,
        'Работы выполнены в полном объёме, в срок, надлежащего качества. '
        'Претензий по объёму, срокам и качеству оказанных услуг стороны '
        'не имеют. Настоящий акт составлен в двух экземплярах, по одному '
        'для каждой из сторон.')

    _add_signatures(doc)

    out = OUT_DIR / 'planned.dotx'
    doc.save(out)
    return out


# ---------------------------------------------------------------------------
# 2. Обслуживание (maintenance.docx) — короче planned
# ---------------------------------------------------------------------------


def gen_maintenance() -> Path:
    doc = Document()
    _set_default_font(doc)

    _add_title(doc, 'АКТ № {{ order.number }}')
    _add_paragraph(doc, 'о проведении технического обслуживания',
                   align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()

    _add_kv_row(doc, 'Договор', '№ {{ contract.number }} от {{ contract.date_of_consclusion }}')
    _add_kv_row(doc, 'Заказчик', '{{ customer.name }} (ИНН {{ customer.inn }})')
    _add_kv_row(doc, 'Исполнитель', '{{ executor.name }} (ИНН {{ executor.inn }})')
    _add_kv_row(doc, 'Объект', '{{ object.name }}, {{ object.address }}')
    _add_kv_row(doc, 'Дата работ', '{{ today_long }}')
    _add_kv_row(doc, 'Исполнитель работ', '{{ user.full_name }} ({{ user.role_name }})')
    doc.add_paragraph()

    _add_paragraph(doc, 'Перечень обслуженного оборудования:', bold=True)
    _add_equipment_table(doc)

    _add_paragraph(doc, 'Описание работ:', bold=True)
    _add_paragraph(doc, '{{ order.description }}')
    doc.add_paragraph()

    _add_paragraph(doc, 'Работы приняты Заказчиком без замечаний.')

    _add_signatures(doc)

    out = OUT_DIR / 'maintenance.docx'
    doc.save(out)
    return out


# ---------------------------------------------------------------------------
# 3. Аварийная заявка (emergency.docx) — без таблицы оборудования
# ---------------------------------------------------------------------------


def gen_emergency() -> Path:
    doc = Document()
    _set_default_font(doc)

    _add_title(doc, 'АКТ № {{ order.number }}')
    _add_paragraph(doc, 'выполнения аварийно-восстановительных работ',
                   align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()

    _add_kv_row(doc, 'Дата составления акта', '{{ today_long }}')
    _add_kv_row(doc, 'Дата поступления заявки', '{{ order.created_at }}')
    _add_kv_row(doc, 'Договор', '№ {{ contract.number }} от {{ contract.date_of_consclusion }}')
    doc.add_paragraph()

    _add_paragraph(doc, 'Стороны:', bold=True)
    _add_kv_row(doc, 'Заказчик', '{{ customer.name }}')
    _add_kv_row(doc, 'В лице', '{{ customer.director_full_name }}')
    _add_kv_row(doc, 'Исполнитель', '{{ executor.name }}')
    _add_kv_row(doc, 'В лице', '{{ executor.director_full_name }}')
    doc.add_paragraph()

    _add_paragraph(doc, 'Объект:', bold=True)
    _add_kv_row(doc, 'Наименование', '{{ object.name }}')
    _add_kv_row(doc, 'Адрес', '{{ object.address }}')
    _add_kv_row(doc, 'Контактное лицо', '{{ object.responsible_face }}, {{ object.responsible_faces_contact }}')
    doc.add_paragraph()

    _add_paragraph(doc, 'Описание неисправности и выполненных работ:', bold=True)
    _add_paragraph(doc, '{{ order.description }}')
    doc.add_paragraph()

    _add_paragraph(doc,
        'Аварийные работы выполнены силами Исполнителя. Оборудование '
        'приведено в рабочее состояние. Претензий у Заказчика нет.')

    _add_signatures(doc)

    out = OUT_DIR / 'emergency.docx'
    doc.save(out)
    return out


# ---------------------------------------------------------------------------
# 4. Первичный осмотр (primary.dotx)
# ---------------------------------------------------------------------------


def gen_primary() -> Path:
    doc = Document()
    _set_default_font(doc)

    _add_title(doc, 'АКТ № {{ order.number }}')
    _add_paragraph(doc, 'первичного осмотра инженерных систем объекта',
                   align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()

    _add_kv_row(doc, 'г. Москва', '{{ today_long }}')
    _add_kv_row(doc, 'Основание', 'договор № {{ contract.number }} от {{ contract.date_of_consclusion }}')
    _add_kv_row(doc, 'Предмет договора', '{{ contract.subject }}')
    doc.add_paragraph()

    _add_paragraph(doc, 'Комиссия в составе представителей:', bold=True)
    _add_paragraph(doc, '— от Заказчика: {{ customer.director_full_name }} ({{ customer.name }});')
    _add_paragraph(doc, '— от Исполнителя: {{ user.full_name }}, {{ user.role_name }} ({{ executor.name }}),')
    _add_paragraph(doc, 'провела первичный осмотр объекта:')
    doc.add_paragraph()

    _add_kv_row(doc, 'Объект', '{{ object.name }}')
    _add_kv_row(doc, 'Адрес', '{{ object.address }}')
    _add_kv_row(doc, 'Ответственный на объекте', '{{ object.responsible_face }}, {{ object.responsible_faces_contact }}')
    doc.add_paragraph()

    _add_paragraph(doc, 'Установлено наличие следующего оборудования:', bold=True)
    _add_equipment_table(doc)

    _add_paragraph(doc, 'Дополнительные замечания:', bold=True)
    _add_paragraph(doc, '{{ order.description }}')
    doc.add_paragraph()

    _add_paragraph(doc,
        'Объект принят на обслуживание в состоянии, соответствующем '
        'условиям договора. Оборудование пригодно для дальнейшей '
        'эксплуатации и планового технического обслуживания.')

    _add_signatures(doc)

    out = OUT_DIR / 'primary.dotx'
    doc.save(out)
    return out


# ---------------------------------------------------------------------------
# 5. Журнал ТО (journal_maint.docx) — паспорт объекта + пустая таблица записей
# ---------------------------------------------------------------------------


def _add_journal_log_table(doc: Document, rows: int = 8) -> None:
    """Пустая таблица для ручных записей ТО: № / Дата / Что сделано /
    Исполнитель / Подпись. Строки только header + N пустых — журнал же
    заполняется по мере обслуживания."""
    table = doc.add_table(rows=1 + rows, cols=5)
    table.style = 'Table Grid'
    table.autofit = False
    widths = (Cm(1.2), Cm(2.5), Cm(6.8), Cm(3.5), Cm(3.0))
    for i, w in enumerate(widths):
        table.columns[i].width = w

    headers = ('№', 'Дата', 'Описание выполненных работ', 'Исполнитель', 'Подпись')
    for cell, text in zip(table.rows[0].cells, headers):
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = cell.paragraphs[0].add_run(text)
        run.bold = True

    for i in range(rows):
        row = table.rows[i + 1].cells
        row[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        row[0].paragraphs[0].add_run(str(i + 1))
    doc.add_paragraph()


def gen_journal_maint() -> Path:
    """Журнал технического обслуживания. Контекст журнала (см.
    render_docx.py::_build_journal_context): object.*, contract.*,
    customer.*, executor.*, today, today_long — **без** order.* и
    equipment_groups. Поэтому таблица оборудования не выводится, но
    в шапке есть все паспортные поля."""
    doc = Document()
    _set_default_font(doc)

    _add_title(doc, 'ЖУРНАЛ')
    _add_paragraph(doc, 'учёта работ по техническому обслуживанию',
                   align=WD_ALIGN_PARAGRAPH.CENTER, bold=True)
    doc.add_paragraph()

    _add_paragraph(doc, 'Сведения об объекте:', bold=True)
    _add_kv_row(doc, 'Наименование', '{{ object.name }}')
    _add_kv_row(doc, 'Адрес', '{{ object.address }}')
    _add_kv_row(doc, 'Ответственный на объекте', '{{ object.responsible_face }}')
    _add_kv_row(doc, 'Контактный телефон', '{{ object.responsible_faces_contact }}')
    doc.add_paragraph()

    _add_paragraph(doc, 'Сведения о договоре обслуживания:', bold=True)
    _add_kv_row(doc, 'Договор', '№ {{ contract.number }} от {{ contract.date_of_consclusion }}')
    _add_kv_row(doc, 'Действует до', '{{ contract.date_of_completion }}')
    _add_kv_row(doc, 'Предмет', '{{ contract.subject }}')
    _add_kv_row(doc, 'Заказчик', '{{ customer.name }} (ИНН {{ customer.inn }})')
    _add_kv_row(doc, 'Исполнитель', '{{ executor.name }} (ИНН {{ executor.inn }})')
    doc.add_paragraph()

    _add_paragraph(doc, 'Журнал заведён:', bold=True)
    _add_kv_row(doc, 'Дата', '{{ today_long }}')
    doc.add_paragraph()

    _add_paragraph(doc, 'Записи о выполненных работах:', bold=True)
    _add_journal_log_table(doc, rows=10)

    _add_paragraph(doc,
        'Журнал ведётся в двух экземплярах: один хранится у Заказчика, '
        'второй — у Исполнителя. Записи вносятся после каждого выхода '
        'на объект и подписываются ответственным лицом Заказчика.')

    out = OUT_DIR / 'journal_maint.docx'
    doc.save(out)
    return out


# ---------------------------------------------------------------------------
# 6. Журнал первичного осмотра (journal_primary.docx)
# ---------------------------------------------------------------------------


def _add_journal_inspection_table(doc: Document, rows: int = 6) -> None:
    """Таблица первичного осмотра: № / Система / Обнаруженное состояние /
    Замечания. Пустые строки — комиссия заполняет вручную по итогам обхода."""
    table = doc.add_table(rows=1 + rows, cols=4)
    table.style = 'Table Grid'
    table.autofit = False
    widths = (Cm(1.2), Cm(4.5), Cm(6.0), Cm(5.3))
    for i, w in enumerate(widths):
        table.columns[i].width = w

    headers = ('№', 'Система / оборудование', 'Состояние на момент осмотра', 'Замечания')
    for cell, text in zip(table.rows[0].cells, headers):
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = cell.paragraphs[0].add_run(text)
        run.bold = True

    for i in range(rows):
        row = table.rows[i + 1].cells
        row[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        row[0].paragraphs[0].add_run(str(i + 1))
    doc.add_paragraph()


def gen_journal_primary() -> Path:
    """Журнал первичного осмотра. Отличается от акта первичного осмотра
    тем, что это долгоживущий документ для регистрации периодических
    осмотров, а не одноразовый акт."""
    doc = Document()
    _set_default_font(doc)

    _add_title(doc, 'ЖУРНАЛ')
    _add_paragraph(doc, 'первичного осмотра и приёмки объекта в обслуживание',
                   align=WD_ALIGN_PARAGRAPH.CENTER, bold=True)
    doc.add_paragraph()

    _add_paragraph(doc, 'Сведения об объекте:', bold=True)
    _add_kv_row(doc, 'Наименование', '{{ object.name }}')
    _add_kv_row(doc, 'Адрес', '{{ object.address }}')
    _add_kv_row(doc, 'Ответственный на объекте', '{{ object.responsible_face }}')
    _add_kv_row(doc, 'Контактный телефон', '{{ object.responsible_faces_contact }}')
    doc.add_paragraph()

    _add_paragraph(doc, 'Стороны:', bold=True)
    _add_kv_row(doc, 'Заказчик', '{{ customer.name }}, ИНН {{ customer.inn }}, КПП {{ customer.kpp }}')
    _add_kv_row(doc, 'Директор', '{{ customer.director_full_name }}')
    _add_kv_row(doc, 'Юр. адрес заказчика', '{{ customer.address }}')
    _add_kv_row(doc, 'Исполнитель', '{{ executor.name }}, ИНН {{ executor.inn }}, КПП {{ executor.kpp }}')
    _add_kv_row(doc, 'Директор', '{{ executor.director_full_name }}')
    _add_kv_row(doc, 'Юр. адрес исполнителя', '{{ executor.address }}')
    doc.add_paragraph()

    _add_paragraph(doc, 'Основание:', bold=True)
    _add_kv_row(doc, 'Договор', '№ {{ contract.number }} от {{ contract.date_of_consclusion }}')
    _add_kv_row(doc, 'Предмет договора', '{{ contract.subject }}')
    doc.add_paragraph()

    _add_paragraph(doc, 'Дата открытия журнала: {{ today_long }}')
    doc.add_paragraph()

    _add_paragraph(doc, 'Результаты осмотра инженерных систем:', bold=True)
    _add_journal_inspection_table(doc, rows=8)

    _add_paragraph(doc,
        'По результатам первичного осмотра объект принимается на '
        'техническое обслуживание в соответствии с условиями договора.')
    doc.add_paragraph()

    _add_signatures(doc)

    out = OUT_DIR / 'journal_primary.docx'
    doc.save(out)
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    if not OUT_DIR.exists():
        OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f'[generate_demo_templates] output: {OUT_DIR}')
    for gen in (gen_planned, gen_maintenance, gen_emergency, gen_primary,
                gen_journal_maint, gen_journal_primary):
        out = gen()
        size = out.stat().st_size
        print(f'  [ok] {out.name} ({size:,} bytes)')
    print('done.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
