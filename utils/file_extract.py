from __future__ import annotations

import re
import zipfile
from collections import Counter
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tif", ".tiff"}
TEXT_EXTRACT_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", *IMAGE_EXTENSIONS}
STRUCTURED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".json"}
SUPPORTED_EXTENSIONS = {*TEXT_EXTRACT_EXTENSIONS, *STRUCTURED_EXTENSIONS, ".zip"}


class ExtractedText(str):
    def __new__(cls, text: str, source: str = "text"):
        instance = super().__new__(cls, text)
        instance.source = source
        return instance

# 页码 / 页眉页脚残留 / OCR 噪声
_PAGE_NOISE_RE = re.compile(
    r"^\s*(?:[-—–]\s*)?\d{1,4}\s*(?:[-—–])?\s*$"
    r"|^\s*第\s*\d{1,4}\s*页(?:\s*[/,，]?\s*共\s*\d{1,4}\s*页)?\s*$"
    r"|^\s*共\s*\d{1,4}\s*页\s*$"
    r"|^\s*page\s*\d{1,4}(\s*(?:of|/)\s*\d{1,4})?\s*$",
    re.IGNORECASE,
)
_CJK = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
_CJK_CHAR_RE = re.compile(f"[{_CJK}]")
_CJK_GAP_RE = re.compile(rf"(?<=[{_CJK}])[ \t]+(?=[{_CJK}])")
_INVISIBLE_RE = re.compile(r"[\u200b\u200c\u200d\ufeff\u00ad]")


def _collapse_spaced_cjk(line: str) -> str:
    """只在「整行每个字之间都插了空格」时合并（PDF 常见），保留“第一章 基础”这类正常空格。"""
    parts = [part for part in line.split(" ") if part]
    if len(parts) < 3:
        return line
    if all(len(part) == 1 and _CJK_CHAR_RE.match(part) for part in parts):
        return "".join(parts)
    return line


def is_supported_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS


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


def clean_extracted_text(text: str) -> str:
    """统一清洗：去不可见字符、合并多余空行、去掉页码与中文之间多余空格。"""
    if not text:
        return ""
    text = _INVISIBLE_RE.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    text = text.replace("\u00a0", " ").replace("\u3000", " ")

    kept_lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            kept_lines.append("")
            continue
        if _PAGE_NOISE_RE.match(stripped):
            continue
        kept_lines.append(_collapse_spaced_cjk(line.rstrip()))

    text = "\n".join(kept_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_from_txt(file_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk", "gb2312", "big5"):
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

    try:
        reader = PdfReader(BytesIO(file_bytes))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"PDF 文件无法读取: {exc}") from exc

    pages: list[list[str]] = []
    ocr_used = False
    for page in reader.pages:
        try:
            raw = page.extract_text() or ""
        except Exception:
            raw = ""
        if not raw.strip():
            ocr_pages: list[str] = []
            try:
                images = list(page.images)
            except Exception:
                images = []
            for image in images:
                try:
                    ocr_text = _extract_from_image(image.data)
                except Exception:
                    continue
                if ocr_text.strip():
                    ocr_pages.append(ocr_text)
                    ocr_used = True
            raw = "\n".join(ocr_pages)
        pages.append([line.rstrip() for line in raw.split("\n") if line.strip()])

    # 跨页重复出现的页眉/页脚：只看每页最前/最后两行，避免误删正文
    if len(pages) >= 3:
        counter: Counter[str] = Counter()
        for lines in pages:
            edge_lines = {item.strip() for item in (lines[:2] + lines[-2:])}
            for line in edge_lines:
                counter[line] += 1
        threshold = max(2, int(len(pages) * 0.6))
        repeated = {
            line
            for line, count in counter.items()
            if count >= threshold
            and len(line) <= 60
            and not re.match(
                r"^(?:正确答案|参考答案|标准答案|答案|答案解析|解析|详解|[A-Ha-h]\s*[.、):])",
                line,
            )
        }
    else:
        repeated = set()

    cleaned_pages: list[str] = []
    for lines in pages:
        kept = [line for line in lines if line.strip() not in repeated]
        if kept:
            cleaned_pages.append("\n".join(kept))
    text = "\n\n".join(cleaned_pages).strip()
    return ExtractedText(text, "ocr" if ocr_used else "text")


def _iter_docx_blocks(document):
    """按文档正文顺序遍历段落与表格。"""
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def _docx_cell_text(cell) -> str:
    return "\n".join(paragraph.text.strip() for paragraph in cell.paragraphs).strip()


def _docx_table_questions(table) -> list[dict] | None:
    if not table.rows:
        return None
    aliases = {
        "章节": "chapter_name",
        "chapter": "chapter_name",
        "chaptername": "chapter_name",
        "题型": "type",
        "type": "type",
        "题干": "content",
        "题目": "content",
        "问题": "content",
        "content": "content",
        "question": "content",
        "答案": "answer",
        "正确答案": "answer",
        "answer": "answer",
        "解析": "explanation",
        "答案解析": "explanation",
        "explanation": "explanation",
        "选项": "options",
        "options": "options",
    }
    for letter in "ABCDEFGH":
        aliases[f"选项{letter}"] = f"option_{letter}"
        aliases[f"option{letter.lower()}"] = f"option_{letter}"
        aliases[letter.lower()] = f"option_{letter}"

    headers = ["".join(_docx_cell_text(cell).split()).lower().replace("_", "") for cell in table.rows[0].cells]
    indexes = {key: index for index, header in enumerate(headers) if (key := aliases.get(header))}
    if "content" not in indexes or not {"answer", "options", "option_A"}.intersection(indexes):
        return None

    questions: list[dict] = []
    for row in table.rows[1:]:
        values = [_docx_cell_text(cell) for cell in row.cells]
        if not any(values):
            continue
        item = {
            key: values[index] if index < len(values) else ""
            for key, index in indexes.items()
            if not key.startswith("option_")
        }
        options = {
            key[-1]: values[index]
            for key, index in indexes.items()
            if key.startswith("option_") and index < len(values) and values[index]
        }
        item["type"] = item.get("type") or "single"
        item["options"] = options or item.get("options", "")
        item["_raw"] = "\n".join(value for value in values if value)
        questions.append(item)
    return questions


def extract_docx_content(file_bytes: bytes) -> tuple[str, list[dict]]:
    try:
        from docx import Document
    except Exception as exc:
        raise HTTPException(status_code=500, detail="服务器未安装 Word 解析依赖 python-docx") from exc
    try:
        document = Document(BytesIO(file_bytes))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Word 文件无法读取: {exc}") from exc

    lines: list[str] = []
    questions: list[dict] = []
    for block in _iter_docx_blocks(document):
        if hasattr(block, "rows"):
            table_questions = _docx_table_questions(block)
            if table_questions is not None:
                questions.extend(table_questions)
                continue
            for row in block.rows:
                cells: list[str] = []
                seen: set[int] = set()
                for cell in row.cells:
                    if id(cell._tc) in seen:
                        continue
                    seen.add(id(cell._tc))
                    value = _docx_cell_text(cell)
                    if value:
                        cells.append(value)
                if cells:
                    lines.append("\n".join(cells))
        else:
            text = block.text.strip()
            if text:
                lines.append(text)
    return "\n".join(lines).strip(), questions


def _extract_from_docx(file_bytes: bytes) -> str:
    return extract_docx_content(file_bytes)[0]


def _extract_from_image(file_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image, ImageEnhance, ImageFilter, ImageSequence
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
        if width < 1600 or height < 1200:
            scale = max(1600 / width, 1200 / height)
            image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)

        image = ImageEnhance.Contrast(image).enhance(1.6)
        image = ImageEnhance.Sharpness(image).enhance(2.0)
        image = image.convert("L").filter(ImageFilter.MedianFilter(size=3))

        candidates: list[tuple[int, int, str]] = []
        last_error: Exception | None = None
        from .parser import parse_exercise_text_detailed

        for psm in (6, 4, 11):
            try:
                raw_text = pytesseract.image_to_string(
                    image,
                    lang="chi_sim+eng",
                    config=f"--oem 3 --psm {psm}",
                )
            except Exception as exc:
                last_error = exc
                continue
            text = _clean_ocr_text(raw_text)
            if not text:
                continue
            parsed = parse_exercise_text_detailed(text)
            candidates.append((len(parsed["questions"]), len(text), text))
        if not candidates:
            if last_error:
                raise last_error
            return ""
        return max(candidates, key=lambda item: (item[0], item[1]))[2]
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"图片 OCR 失败: {exc}. 请确认已安装 Tesseract OCR，并包含 chi_sim 和 eng 语言包。",
        ) from exc


def _clean_ocr_text(text: str) -> str:
    """OCR 常见错误修正：中文之间空格、成对符号错位、孤立单字行。"""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 全角标点统一（选项字母等由 parser 侧折行处理）
    text = text.translate(str.maketrans({"：": ":", "（": "(", "）": ")", "．": ".", "　": " "}))
    lines: list[str] = []
    for line in text.split("\n"):
        stripped = _CJK_GAP_RE.sub("", line.strip())
        if not stripped:
            continue
        # OCR 偶尔把页码识别成孤立数字
        if _PAGE_NOISE_RE.match(stripped):
            continue
        lines.append(stripped)
    return "\n".join(lines).strip()


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

    source = "ocr" if suffix in IMAGE_EXTENSIONS or getattr(text, "source", "text") == "ocr" else "text"
    text = clean_extracted_text(text) if suffix not in IMAGE_EXTENSIONS else text.strip()
    if not text.strip():
        if suffix in IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="图片解析成功，但未识别到文本内容。可改用智能解析重试，或确保图片清晰、方向正确。",
            )
        raise HTTPException(status_code=400, detail="文件解析成功，但未提取到文本内容")
    return ExtractedText(text, source)


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
