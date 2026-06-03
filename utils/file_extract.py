from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException


def _extract_from_txt(file_bytes: bytes) -> str:
    for encoding in ("utf-8", "gbk", "gb2312"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="文本文件编码无法识别，请使用 UTF-8/GBK")


def _extract_from_pdf(file_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="服务器未安装 PDF 解析依赖 pypdf") from exc

    reader = PdfReader(BytesIO(file_bytes))
    texts: list[str] = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return "\n".join(texts).strip()


def _extract_from_docx(file_bytes: bytes) -> str:
    try:
        from docx import Document
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="服务器未安装 Word 解析依赖 python-docx") from exc

    document = Document(BytesIO(file_bytes))
    return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()


def _extract_from_image(file_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="服务器未安装图片 OCR 依赖 Pillow/pytesseract") from exc

    try:
        image = Image.open(BytesIO(file_bytes))
        text = pytesseract.image_to_string(image, lang="chi_sim+eng")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"图片 OCR 失败：{exc}") from exc
    return text.strip()


def extract_text_from_file(filename: str, file_bytes: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        text = _extract_from_txt(file_bytes)
    elif suffix == ".pdf":
        text = _extract_from_pdf(file_bytes)
    elif suffix == ".docx":
        text = _extract_from_docx(file_bytes)
    elif suffix in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
        text = _extract_from_image(file_bytes)
    else:
        raise HTTPException(status_code=400, detail="仅支持 txt/md/pdf/docx/png/jpg/jpeg/bmp/webp 文件")

    if not text.strip():
        raise HTTPException(status_code=400, detail="文件解析成功，但未提取到文本内容")
    return text


def save_uploaded_file(filename: str, file_bytes: bytes, upload_dir: Path) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid4().hex}{suffix}"
    saved_path = upload_dir / safe_name
    saved_path.write_bytes(file_bytes)
    return safe_name, suffix


def extract_zip_file(file_bytes: bytes, upload_dir: Path) -> list[dict]:
    """解压zip文件并返回内部文件列表，每个文件包含filename、file_bytes、suffix"""
    result = []
    try:
        with zipfile.ZipFile(BytesIO(file_bytes), 'r') as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue  # 跳过目录
                if member.filename.startswith('__MACOSX') or member.filename.startswith('.'):
                    continue  # 跳过系统文件
                try:
                    extracted_bytes = zf.read(member)
                    suffix = Path(member.filename).suffix.lower()
                    result.append({
                        'filename': Path(member.filename).name,
                        'file_bytes': extracted_bytes,
                        'suffix': suffix
                    })
                except Exception:
                    continue
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="无效的zip文件")
    return result
