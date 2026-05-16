# service/attachment_converter.py
"""
Конвертация загруженных пользователем файлов (фото / готовый PDF) в один PDF-документ.

- Поддерживаются JPEG, PNG, WEBP, TIFF, HEIC/HEIF, а также готовые PDF.
- Один аттач = один PDF (несколько фото в одном аттаче склеиваются в многостраничный PDF).
- Лимиты: размер каждого файла ≤ MAX_FILE_SIZE, всего файлов в одном аттаче ≤ MAX_FILES_PER_ATTACHMENT.
- Реальный формат определяется по содержимому (Pillow / pypdf), а не по расширению.
"""
import io
from typing import List, Tuple

import img2pdf
from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pillow_heif import register_heif_opener
from pypdf import PdfReader

# Регистрируем поддержку HEIC/HEIF в Pillow.
register_heif_opener()

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB на один файл
MAX_FILES_PER_ATTACHMENT = 10
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP", "TIFF", "HEIF"}


async def convert_uploads_to_pdf(files: List[UploadFile]) -> Tuple[bytes, int]:
    """
    Сконвертировать список загруженных файлов в один PDF.

    Returns:
        (pdf_bytes, pages)

    Raises:
        HTTPException 400 — невалидные / слишком большие файлы / неподдерживаемый формат.
    """
    if not files:
        raise HTTPException(status_code=400, detail="Не передано ни одного файла")
    if len(files) > MAX_FILES_PER_ATTACHMENT:
        raise HTTPException(
            status_code=400,
            detail=f"Слишком много файлов в одном вложении (максимум {MAX_FILES_PER_ATTACHMENT})",
        )

    # Считываем все файлы в память с проверкой лимитов.
    raw_payloads: List[Tuple[str, bytes]] = []
    for upload in files:
        data = await upload.read()
        if not data:
            raise HTTPException(
                status_code=400,
                detail=f"Файл '{upload.filename}' пустой",
            )
        if len(data) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Файл '{upload.filename}' превышает лимит "
                    f"{MAX_FILE_SIZE // (1024 * 1024)} МБ"
                ),
            )
        raw_payloads.append((upload.filename or "file", data))

    # Один готовый PDF — пропускаем без перекодирования, просто считаем страницы.
    if len(raw_payloads) == 1 and _looks_like_pdf(raw_payloads[0][1]):
        pdf_bytes = raw_payloads[0][1]
        pages = _count_pdf_pages(pdf_bytes, raw_payloads[0][0])
        return pdf_bytes, pages

    # Несколько файлов или одно изображение → нормализуем каждое в JPEG-байты и собираем PDF.
    image_payloads: List[bytes] = []
    for filename, data in raw_payloads:
        if _looks_like_pdf(data):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Файл '{filename}' — PDF. Готовый PDF можно загрузить только один, "
                    "и без других файлов в этом вложении."
                ),
            )
        image_payloads.append(_normalize_image_to_jpeg(data, filename))

    try:
        pdf_bytes = img2pdf.convert(image_payloads)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Не удалось собрать PDF из изображений: {exc}",
        )
    return pdf_bytes, len(image_payloads)


def _looks_like_pdf(data: bytes) -> bool:
    return data[:5] == b"%PDF-"


def _count_pdf_pages(data: bytes, filename: str) -> int:
    try:
        reader = PdfReader(io.BytesIO(data))
        return len(reader.pages)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Файл '{filename}' не является корректным PDF: {exc}",
        )


def _normalize_image_to_jpeg(data: bytes, filename: str) -> bytes:
    """
    Открыть изображение через Pillow, проверить формат, привести к baseline JPEG (RGB)
    и вернуть байты, пригодные для img2pdf.
    """
    try:
        with Image.open(io.BytesIO(data)) as img:
            img_format = (img.format or "").upper()
            if img_format not in ALLOWED_IMAGE_FORMATS:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Формат файла '{filename}' ({img_format or 'неизвестно'}) не поддерживается. "
                        "Допустимы: JPEG, PNG, WEBP, TIFF, HEIC."
                    ),
                )
            img.load()
            if img.mode != "RGB":
                img = img.convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=92, optimize=True)
            return buf.getvalue()
    except HTTPException:
        raise
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=400,
            detail=f"Файл '{filename}' не является изображением",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Не удалось обработать файл '{filename}': {exc}",
        )
