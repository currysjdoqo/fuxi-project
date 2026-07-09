from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tif", ".tiff"}
TEXT_EXTRACT_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", *IMAGE_EXTENSIONS}


def _configure_tesseract_binary(pytesseract_module) -> None:
    current_cmd = getattr(pytesseract_module.pytesseract, "tesseract_cmd", "") or ""
    if current_cmd and Path(current_cmd).is_file():
        return

    candidates = [
        Path("F:/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
        Path.home() / "AppData/Local/Programs/Tesseract-OCR/tesseract.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            pytesseract_module.pytesseract.tesseract_cmd = str(candidate)
            return


def _extract_from_txt(file_bytes: bytes) -> str:
    for encoding in ("utf-8", "gbk", "gb2312"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="文本文件编码无法识别，请使用 UTF-8 或 GBK")


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
        from PIL import Image, ImageSequence, ImageEnhance
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="服务器未安装图片 OCR 依赖 Pillow 或 pytesseract") from exc

    try:
        _configure_tesseract_binary(pytesseract)
        image = Image.open(BytesIO(file_bytes))
        if getattr(image, "is_animated", False):
            image = next(ImageSequence.Iterator(image))
        
        if image.mode not in {"L", "RGB"}:
            image = image.convert("RGB")
        
        width, height = image.size
        if width < 800 or height < 600:
            scale = max(800 / width, 600 / height)
            image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
        
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        gray = image.convert("L")
        threshold = 128
        binary = gray.point(lambda x: 0 if x < threshold else 255, '1')
        
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz一乙二三四五六七八九十百千万亿零壹贰叁肆伍陆柒捌玖拾佰仟万亿〇、，。？！：；“”‘’（）【】《》〈〉·…—━─│\|—－－～～々※∞★☆●○◎◇◆□■△▲▼▽⊿◢◣◤◥☉⊕⊙⊿◈◇†‡◊·▪▫▬▭▮▯▰▱▲△▴▵▶▷▸▹►▻▼▽▾▿◀◁◂◃◄◅◢◣◤◥◬◭◮◯◰◱◲◳◴◵◶◷◸◹◺◻◼◽◾◿☺☻☹☺☻☹'
        
        text = pytesseract.image_to_string(binary, lang="chi_sim+eng", config=custom_config)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"图片 OCR 失败: {exc}. 请确认已安装 Tesseract OCR，并包含 chi_sim 和 eng 语言包。",
        ) from exc
    return text.strip()


def extract_text_from_file(filename: str, file_bytes: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        text = _extract_from_txt(file_bytes)
    elif suffix == ".pdf":
        text = _extract_from_pdf(file_bytes)
    elif suffix == ".docx":
        text = _extract_from_docx(file_bytes)
    elif suffix in IMAGE_EXTENSIONS:
        text = _extract_from_image(file_bytes)
    else:
        raise HTTPException(
            status_code=400,
            detail="仅支持 txt/md/pdf/docx/png/jpg/jpeg/bmp/webp/gif/tif/tiff 文件",
        )

    if not text.strip():
        if suffix in IMAGE_EXTENSIONS:
            raise HTTPException(status_code=400, detail="图片解析成功，但未识别到文本内容。请尝试使用 AI 兜底解析功能，或确保图片中的文字清晰可读。")
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
    result = []
    try:
        with zipfile.ZipFile(BytesIO(file_bytes), "r") as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                if member.filename.startswith("__MACOSX") or member.filename.startswith("."):
                    continue
                try:
                    extracted_bytes = zf.read(member)
                    suffix = Path(member.filename).suffix.lower()
                    result.append(
                        {
                            "filename": Path(member.filename).name,
                            "file_bytes": extracted_bytes,
                            "suffix": suffix,
                        }
                    )
                except Exception:
                    continue
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="无效的 zip 文件")
    return result
