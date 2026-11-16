"""章节复习资料的内存导出工具。"""

import re
from functools import lru_cache
from io import BytesIO
from xml.sax.saxutils import escape

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer


_HEADING_RE = re.compile(r"^(\s*)(#{1,6})\s+(.+?)\s*$")
_BULLET_RE = re.compile(r"^(\s*)[-+*]\s+(.+)$")
_NUMBER_RE = re.compile(r"^(\s*)(\d+[.)])\s+(.+)$")
_BOLD_RE = re.compile(r"(\*\*.*?\*\*)")

# XML 1.0 不允许的控制字符与孤立代理项：docx（lxml）遇到会直接抛
# ValueError: All strings must be XML compatible，导致整次导出 500。
# 另外 str.splitlines() 会把 \x0b/\x0c 等当成换行，导出前统一清理，
# 避免同一段内容在 md/docx/pdf 之间出现不一致的换行。
_FORBIDDEN_CHAR_RE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


def _clean_text(value):
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    if not text:
        return ""
    return _FORBIDDEN_CHAR_RE.sub("", text)


def _outline_items(outline):
    if isinstance(outline, dict):
        outline = outline.get("outline")
    if not isinstance(outline, list):
        return []

    items = []

    def walk(nodes, depth):
        if not isinstance(nodes, list):
            return
        for node in nodes:
            children = None
            if isinstance(node, dict):
                title = node.get("title", node.get("name", ""))
                children = node.get("children")
            elif isinstance(node, (str, int, float)):
                title = node
            else:
                continue
            title = str(title).strip() if title is not None else ""
            title = _clean_text(title).strip()
            if title:
                items.append((depth, title))
            if children:
                walk(children, depth + 1)

    walk(outline, 0)
    return items


def _shift_markdown_headings(markdown):
    lines = []
    for line in markdown.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            indent, marks, text = match.groups()
            line = f"{indent}{'#' * min(len(marks) + 2, 6)} {text}"
        lines.append(line)
    return "\n".join(lines)


def _markdown_outline(outline):
    return "\n".join(
        f"{'  ' * depth}- {title}" for depth, title in _outline_items(outline)
    )


def export_chapters_to_md(chapters):
    blocks = []
    for chapter in chapters:
        summary = _clean_text(chapter.get("summary_md")).strip()
        outline = _markdown_outline(chapter.get("outline_json"))
        blocks.append(
            f"# {_clean_text(chapter.get('name'))}\n\n"
            f"## 知识点总结\n\n"
            f"{_shift_markdown_headings(summary) if summary else '尚未生成'}\n\n"
            f"## 知识大纲\n\n{outline or '尚未生成'}"
        )
    buffer = BytesIO()
    buffer.write(("\n\n---\n\n".join(blocks) + "\n").encode("utf-8"))
    return buffer.getvalue()


def _configure_docx_fonts(document):
    for style in document.styles:
        if style.type != 1:  # WD_STYLE_TYPE.PARAGRAPH
            continue
        font_name = "黑体" if style.name.startswith(("Heading", "Title")) else "宋体"
        style.font.name = font_name
        r_pr = style.element.get_or_add_rPr()
        r_fonts = r_pr.get_or_add_rFonts()
        r_fonts.set(qn("w:ascii"), font_name)
        r_fonts.set(qn("w:hAnsi"), font_name)
        r_fonts.set(qn("w:eastAsia"), font_name)


def _docx_style_ids(document):
    """一次性取出要用到的样式 id，避免逐段按名查找样式。"""
    names = ("List Bullet", "List Number") + tuple(
        f"Heading {level}" for level in range(1, 10)
    )
    return {name: document.styles[name].style_id for name in names}


def _add_docx_paragraph(document, style_id=None):
    """新建段落并按 style id 直接写 w:pStyle。

    python-docx 的 ``add_paragraph(style="名字")`` 每次都要在整张样式表
    （默认模板 164 条）里线性查找并解析样式元素，耗时为直接写 id 的数倍；
    这里等价地写入 ``paragraph.style`` setter 最终落到的那一个 pStyle 值。
    """
    paragraph = document.add_paragraph()
    if style_id:
        paragraph._p.style = style_id
    return paragraph


def _add_docx_heading(document, text, style_ids, level):
    paragraph = _add_docx_paragraph(document, style_ids[f"Heading {level}"])
    paragraph.add_run(_clean_text(text))
    return paragraph


def _add_docx_inline(paragraph, text, explicit_non_bold=False):
    """按 ``**加粗**`` 拆分并写入 run。

    ``explicit_non_bold`` 用于标题段落：内置 Heading 1-4 样式本身是加粗的，
    这些段落里的普通文本需要显式 ``run.bold = False`` 才保持原有观感；
    正文/列表段落不受样式影响，跳过这次写入以省掉每个 run 的 rPr 插入。
    """
    for part in _BOLD_RE.split(text):
        if not part:
            continue
        is_bold = part.startswith("**") and part.endswith("**") and len(part) >= 4
        run = paragraph.add_run(part[2:-2] if is_bold else part)
        if is_bold or explicit_non_bold:
            run.bold = is_bold


def _add_docx_summary(document, summary, style_ids):
    if not summary:
        document.add_paragraph("尚未生成")
        return
    for line in summary.splitlines():
        if not line.strip():
            continue
        heading = _HEADING_RE.match(line)
        bullet = _BULLET_RE.match(line)
        number = _NUMBER_RE.match(line)
        if heading:
            _, marks, text = heading.groups()
            paragraph = _add_docx_paragraph(
                document, style_ids[f"Heading {min(len(marks) + 2, 9)}"]
            )
            _add_docx_inline(paragraph, text, explicit_non_bold=True)
        elif bullet:
            indent, text = bullet.groups()
            paragraph = _add_docx_paragraph(document, style_ids["List Bullet"])
            paragraph.paragraph_format.left_indent = Inches(len(indent.expandtabs(4)) / 16)
            _add_docx_inline(paragraph, text)
        elif number:
            indent, _, text = number.groups()
            paragraph = _add_docx_paragraph(document, style_ids["List Number"])
            paragraph.paragraph_format.left_indent = Inches(len(indent.expandtabs(4)) / 16)
            _add_docx_inline(paragraph, text)
        else:
            _add_docx_inline(document.add_paragraph(), line.strip())


def export_chapters_to_docx(chapters):
    document = Document()
    _configure_docx_fonts(document)
    style_ids = _docx_style_ids(document)
    for index, chapter in enumerate(chapters):
        if index:
            document.add_page_break()
        _add_docx_heading(document, chapter.get("name"), style_ids, 1)
        _add_docx_heading(document, "知识点总结", style_ids, 2)
        _add_docx_summary(
            document, _clean_text(chapter.get("summary_md")).strip(), style_ids
        )
        _add_docx_heading(document, "知识大纲", style_ids, 2)
        outline = _outline_items(chapter.get("outline_json"))
        if not outline:
            document.add_paragraph("尚未生成")
        for depth, title in outline:
            paragraph = _add_docx_paragraph(document, style_ids["List Bullet"])
            paragraph.paragraph_format.left_indent = Inches(depth * 0.25)
            _add_docx_inline(paragraph, title)

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _pdf_inline(text):
    rendered = []
    for part in _BOLD_RE.split(text):
        if not part:
            continue
        is_bold = part.startswith("**") and part.endswith("**") and len(part) >= 4
        value = escape(part[2:-2] if is_bold else part)
        rendered.append(f"<b>{value}</b>" if is_bold else value)
    return "".join(rendered)


@lru_cache(maxsize=1)
def _pdf_styles():
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    pdfmetrics.registerFontFamily(
        "STSong-Light",
        normal="STSong-Light",
        bold="STSong-Light",
        italic="STSong-Light",
        boldItalic="STSong-Light",
    )
    body = ParagraphStyle(
        "ChapterBody",
        fontName="STSong-Light",
        fontSize=10.5,
        leading=17,
        alignment=TA_LEFT,
        wordWrap="CJK",
        spaceAfter=6,
    )
    return {
        "chapter": ParagraphStyle(
            "ChapterTitle", parent=body, fontSize=20, leading=28, spaceAfter=18
        ),
        "section": ParagraphStyle(
            "ChapterSection", parent=body, fontSize=15, leading=22, spaceBefore=6, spaceAfter=10
        ),
        "heading": ParagraphStyle(
            "ChapterSummaryHeading", parent=body, fontSize=12.5, leading=20, spaceBefore=5, spaceAfter=8
        ),
        "body": body,
    }


def _pdf_indent_style(styles, cache, left_indent):
    """按左缩进复用段落样式，避免每行都新建一个 ParagraphStyle。"""
    style = cache.get(left_indent)
    if style is None:
        style = ParagraphStyle(
            f"ChapterIndent{left_indent}",
            parent=styles["body"],
            leftIndent=left_indent,
        )
        cache[left_indent] = style
    return style


def _pdf_summary(story, summary, styles, indent_cache):
    if not summary:
        story.append(Paragraph("尚未生成", styles["body"]))
        return
    for line in summary.splitlines():
        if not line.strip():
            story.append(Spacer(1, 4))
            continue
        heading = _HEADING_RE.match(line)
        bullet = _BULLET_RE.match(line)
        number = _NUMBER_RE.match(line)
        if heading:
            _, _, text = heading.groups()
            story.append(Paragraph(_pdf_inline(text), styles["heading"]))
        elif bullet:
            indent, text = bullet.groups()
            style = _pdf_indent_style(
                styles, indent_cache, 18 + len(indent.expandtabs(4)) * 4
            )
            story.append(Paragraph(f"• {_pdf_inline(text)}", style))
        elif number:
            indent, marker, text = number.groups()
            style = _pdf_indent_style(
                styles, indent_cache, 18 + len(indent.expandtabs(4)) * 4
            )
            story.append(Paragraph(f"{marker} {_pdf_inline(text)}", style))
        else:
            story.append(Paragraph(_pdf_inline(line.strip()), styles["body"]))


def export_chapters_to_pdf(chapters):
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=56,
        leftMargin=56,
        topMargin=56,
        bottomMargin=56,
    )
    styles = _pdf_styles()
    indent_cache = {}
    story = []
    for index, chapter in enumerate(chapters):
        if index:
            story.append(PageBreak())
        story.append(Paragraph(_pdf_inline(_clean_text(chapter.get("name"))), styles["chapter"]))
        story.append(Paragraph("知识点总结", styles["section"]))
        _pdf_summary(
            story, _clean_text(chapter.get("summary_md")).strip(), styles, indent_cache
        )
        story.append(Paragraph("知识大纲", styles["section"]))
        outline = _outline_items(chapter.get("outline_json"))
        if not outline:
            story.append(Paragraph("尚未生成", styles["body"]))
        for depth, title in outline:
            style = _pdf_indent_style(styles, indent_cache, depth * 20)
            story.append(Paragraph(f"• {_pdf_inline(title)}", style))
    document.build(story)
    return buffer.getvalue()


_EXPORTERS = {
    "md": export_chapters_to_md,
    "docx": export_chapters_to_docx,
    "pdf": export_chapters_to_pdf,
}


def export_chapters(chapters, file_format):
    return _EXPORTERS[file_format](chapters)
