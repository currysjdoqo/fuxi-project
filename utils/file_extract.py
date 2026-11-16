from __future__ import annotations

import os
import re
import threading
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

# OCR 专属规则表：数据而非逻辑，新增一种错法只需在此追加一行。
# 全角标点/数字归一（选项字母等折行由 parser 侧处理）
_OCR_TRANSLATE = str.maketrans(
    {
        "：": ":",
        "（": "(",
        "）": ")",
        "．": ".",
        **{chr(0xFF10 + digit): str(digit) for digit in range(10)},
    }
)
# 只收「任何中文语境下都不成词」的错形，盲替换也不会误伤正文
_OCR_WORD_FIXES: tuple[tuple[str, str], ...] = (
    ("答桉", "答案"),
    ("答寨", "答案"),
    ("荅案", "答案"),
    ("解忻", "解析"),
    ("解祈", "解析"),
)
# 行首题号被认成 l / I / 丨 / |
_OCR_ENUM_FIX_RE = re.compile(r"^([ \t]*)[lI丨|](?=[.、)])", re.MULTILINE)

# —— 性能旋钮（都用环境变量调，不把经验值写死在逻辑里）——
# 尺寸下限：太小的图先放大（Tesseract 对小字不友好）。
_OCR_MIN_SIZE = (1600, 1200)
# 尺寸上限：默认 0 = 不缩放。实测 12MP 原图缩到 2600px 长边只省 ~0.2s 预处理，
# 却会把选项里的句点抹掉（选项 3→0）、3000px 时还会丢题，属于「省时间换准确率」的亏本买卖。
# 只有在内存吃紧的部署里才值得打开（如 OCR_MAX_EDGE=4000）。
_OCR_MAX_EDGE = int(os.getenv("OCR_MAX_EDGE", "0"))
# Tesseract 是子进程不占 GIL，但 N 个并发请求 × 多趟会互相抢 CPU 和内存，故全局限流。
# 默认跟着 CPU 核数走：4 核机器上 4 个并发 OCR 已经能把核吃满。
_OCR_MAX_WORKERS = max(1, int(os.getenv("OCR_MAX_WORKERS", str(min(4, os.cpu_count() or 2)))))
_OCR_SLOTS = threading.BoundedSemaphore(_OCR_MAX_WORKERS)
# 首趟就切出完整题、覆盖率也达标时，跳过剩余 psm（每趟都是一个 Tesseract 子进程）。
# 阈值复用 SMART_PARSE_MIN_COVERAGE：同一把尺子同时决定「要不要再赌一次版面」和「要不要调 AI」。
# 想恢复「三趟都跑」以求最大召回，设 OCR_FAST_ACCEPT=0。
_OCR_FAST_ACCEPT = os.getenv("OCR_FAST_ACCEPT", "1").strip().lower() not in {"0", "false", "no", "off"}
_OCR_ACCEPT_COVERAGE = float(os.getenv("SMART_PARSE_MIN_COVERAGE", "0.85"))


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


# —— 语言包（traineddata）定位 ——
# 中文题目必须 chi_sim，eng 用来兜住字母、数字与符号；两者缺一都会让识别结果不可用。
_OCR_REQUIRED_LANGS: tuple[str, ...] = ("chi_sim", "eng")
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 项目内语言包目录：data/ 已在 .gitignore，十几 MB 的二进制不入库，但放这里免去改 Program Files。
_LOCAL_TESSDATA_DIRS: tuple[Path, ...] = (
    _PROJECT_ROOT / "data" / "tessdata",
    _PROJECT_ROOT / "assets" / "tessdata",
)
_tessdata_dir_cache: Path | None = None


def _tessdata_candidates(pytesseract_module) -> list[Path]:
    """可能存放 *.traineddata 的目录，按优先级排列（环境变量 → 引擎自带 → 项目内）。"""
    candidates: list[Path] = []
    env_dir = os.getenv("TESSDATA_PREFIX")
    if env_dir:
        candidates.append(Path(env_dir))
    cmd = getattr(pytesseract_module.pytesseract, "tesseract_cmd", "") or ""
    if cmd:
        candidates.append(Path(cmd).parent / "tessdata")
    candidates.extend(
        [
            Path("F:/Tesseract-OCR/tessdata"),
            Path("C:/Program Files/Tesseract-OCR/tessdata"),
            Path("C:/Program Files (x86)/Tesseract-OCR/tessdata"),
            Path.home() / "AppData/Local/Programs/Tesseract-OCR/tessdata",
        ]
    )
    candidates.extend(_LOCAL_TESSDATA_DIRS)

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _missing_ocr_langs(tessdata_dir: Path) -> list[str]:
    return [lang for lang in _OCR_REQUIRED_LANGS if not (tessdata_dir / f"{lang}.traineddata").is_file()]


def ensure_ocr_languages(pytesseract_module) -> Path:
    """确认 Tesseract 拿得到 chi_sim + eng，并把 TESSDATA_PREFIX 指到可用的那个目录。

    为什么不靠 ``--list-langs`` 探测：语言包缺失时 Tesseract 不会报错，而是悄悄用
    eng 去认中文，结果是一屏乱码——错误被推迟到「解析出 0 道题」，排查成本很高。
    所以这里直接看 traineddata 文件在不在，缺了就抛 500 并说清缺什么、该放哪里。
    """
    global _tessdata_dir_cache
    if _tessdata_dir_cache is not None and not _missing_ocr_langs(_tessdata_dir_cache):
        return _tessdata_dir_cache

    scanned: list[str] = []
    for candidate in _tessdata_candidates(pytesseract_module):
        if not candidate.is_dir():
            continue
        missing = _missing_ocr_langs(candidate)
        if missing:
            found = [name for name in ("chi_sim", "eng", "osd") if (candidate / f"{name}.traineddata").is_file()]
            scanned.append(f"{candidate}（有 {', '.join(found)}，缺 {', '.join(missing)}）")
            continue
        # 语言包可能装在项目目录里，而引擎默认只看自己的 tessdata，用环境变量把它指过去。
        os.environ["TESSDATA_PREFIX"] = str(candidate)
        _tessdata_dir_cache = candidate
        return candidate

    cmd = getattr(pytesseract_module.pytesseract, "tesseract_cmd", "") or ""
    engine_dir = Path(cmd).parent / "tessdata" if cmd else _LOCAL_TESSDATA_DIRS[0]
    target = engine_dir if engine_dir.is_dir() else _LOCAL_TESSDATA_DIRS[0]
    detail = (
        "图片 OCR 缺少中文语言包 chi_sim，Tesseract 会把中文当英文识别成乱码。"
        f"请把 chi_sim.traineddata 放到 {target} 目录后重试"
        "（下载地址：https://github.com/tesseract-ocr/tessdata_best/raw/main/chi_sim.traineddata）。"
    )
    if scanned:
        detail += "已检查的目录：" + "；".join(scanned) + "。"
    raise HTTPException(status_code=500, detail=detail)


def clean_extracted_text(text: str, *, ocr: bool = False) -> str:
    """统一清洗：去不可见字符、合并多余空行、去掉页码与中文之间多余空格。

    ``ocr=True`` 时额外做 OCR 专属处理：全角标点/数字归一、常见错字纠正、
    行首题号纠错、中文之间空格合并、丢弃空行。非 OCR 路径行为不变。
    """
    if not text:
        return ""
    text = _INVISIBLE_RE.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    text = text.replace("\u00a0", " ").replace("\u3000", " ")
    if ocr:
        text = text.translate(_OCR_TRANSLATE)
        for wrong, right in _OCR_WORD_FIXES:
            text = text.replace(wrong, right)
        text = _OCR_ENUM_FIX_RE.sub(r"\g<1>1", text)

    kept_lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            if not ocr:  # OCR 输出的空行没有信息量
                kept_lines.append("")
            continue
        if _PAGE_NOISE_RE.match(stripped):
            continue
        kept_lines.append(_CJK_GAP_RE.sub("", stripped) if ocr else _collapse_spaced_cjk(line.rstrip()))

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


def _ocr_candidate_is_complete(candidate: tuple[int, float, int, str]) -> bool:
    """这一趟的识别结果是否好到不必再换版面假设重跑。

    判据与 question_pipeline 的 AI 门控一致：拆出题且覆盖率达标 = 已经"够用"。
    """
    questions, coverage = candidate[0], candidate[1]
    return questions > 0 and coverage >= _OCR_ACCEPT_COVERAGE


def _extract_from_image(file_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image, ImageEnhance, ImageFilter, ImageSequence
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="服务器未安装图片 OCR 依赖 Pillow 或 pytesseract") from exc

    try:
        _configure_tesseract_binary(pytesseract)
        # 先确认 chi_sim 就位：缺语言包时 Tesseract 只会输出乱码而不报错，必须提前拦。
        ensure_ocr_languages(pytesseract)
        image = Image.open(BytesIO(file_bytes))
        if getattr(image, "is_animated", False):
            image = next(ImageSequence.Iterator(image))

        if image.mode not in {"L", "RGB"}:
            image = image.convert("RGB")

        # 注意：这里刻意不加「缩小到长边上限」的逻辑。实测 12MP 原图缩到 2600px 只省 ~0.2s
        # 预处理，却会抹掉选项句点、甚至丢题；解码期抽样的收益也只在大到 2× 上限的图上才出现，
        # 不值得为它加一条会伤准确率的路径。要省内存请显式设 OCR_MAX_EDGE。
        width, height = image.size
        if width and height and (width < _OCR_MIN_SIZE[0] or height < _OCR_MIN_SIZE[1]):
            scale = max(_OCR_MIN_SIZE[0] / width, _OCR_MIN_SIZE[1] / height)
            image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
        elif _OCR_MAX_EDGE and width and height and max(width, height) > _OCR_MAX_EDGE:
            scale = _OCR_MAX_EDGE / max(width, height)
            image = image.resize((int(width * scale), int(height * scale)), Image.Resampling.BILINEAR)

        image = ImageEnhance.Contrast(image).enhance(1.6)
        image = ImageEnhance.Sharpness(image).enhance(2.0)
        image = image.convert("L").filter(ImageFilter.MedianFilter(size=3))

        candidates: list[tuple[int, float, int, str]] = []
        last_error: Exception | None = None
        from .parser import parse_exercise_text_detailed

        # 先用最常见的版面假设（psm 6），够好就收工；不够好再依次换 psm 4（单栏）、11（稀疏文本）。
        with _OCR_SLOTS:
            for psm in (6, 4, 11):
                try:
                    raw_text = pytesseract.image_to_string(
                        image,
                        lang="chi_sim+eng",
                        config=f"--oem 1 --psm {psm} -c preserve_interword_spaces=1 --dpi 300",
                    )
                except Exception as exc:
                    last_error = exc
                    continue
                text = clean_extracted_text(raw_text, ocr=True)
                if not text:
                    continue
                parsed = parse_exercise_text_detailed(text)
                # 选择键与 question_pipeline 的门控用同一个指标：先完整题数，再覆盖率，
                # 最后才是字符数（避免全是 0 题时丢掉内容最多的那一趟）。
                candidate = (
                    len(parsed["questions"]),
                    float(parsed["stats"]["coverage"]),
                    len(text),
                    text,
                )
                candidates.append(candidate)
                if _OCR_FAST_ACCEPT and _ocr_candidate_is_complete(candidate):
                    break
        if not candidates:
            if last_error:
                raise last_error
            return ""
        return max(candidates, key=lambda item: (item[0], item[1], item[2]))[3]
    except HTTPException:
        # 语言包缺失这类「环境问题」已经带了明确的 500 文案，不要被下面的 400 吞掉重写。
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"图片 OCR 失败: {exc}. 请确认已安装 Tesseract OCR，并包含 chi_sim 和 eng 语言包。",
        ) from exc


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
    text = clean_extracted_text(text)
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
