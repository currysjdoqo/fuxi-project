"""
习题导出 API 路由
支持导出练习题为 Word 或 PDF 格式
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
import os

from database import get_db
from models import Question, Subject
from utils.exporter import (
    export_to_word,
    export_to_pdf,
    get_supported_types
)

router = APIRouter(prefix="/export", tags=["导出"])


class QuestionExportItem(BaseModel):
    """导出题目项"""
    id: int


class ExportRequest(BaseModel):
    """导出请求"""
    subject_id: int
    question_ids: Optional[List[int]] = None  # 如果为空，导出该科目所有题目
    format: str = "word"  # word 或 pdf
    include_answer: bool = True
    include_analysis: bool = True
    # 题目类型过滤（单选、多选、判断、填空、简答）
    question_types: Optional[List[str]] = None


class ExportInfo(BaseModel):
    """导出信息"""
    subject_name: str
    total_questions: int
    supported_types: List[str]
    formats: List[dict]


def get_current_user_id() -> int:
    """获取当前用户ID（从认证状态获取）"""
    # 这里简化处理，实际应从token获取
    # 暂时返回 None，使用公共题目
    return None


@router.get("/info", response_model=ExportInfo)
def get_export_info(subject_id: int = Query(...)):
    """获取导出信息"""
    db = next(get_db())
    
    subject = db.query(Subject).filter(
        Subject.id == subject_id
    ).first()
    
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    
    return ExportInfo(
        subject_name=subject.name,
        total_questions=0,  # 实际会统计
        supported_types=get_supported_types(),
        formats=[
            {"value": "word", "label": "Word 文档 (.docx)"},
            {"value": "pdf", "label": "PDF 文档 (.pdf)"}
        ]
    )


@router.post("/preview")
def preview_export(
    subject_id: int = Query(...),
    format: str = Query("word"),
    include_answer: bool = Query(True),
    include_analysis: bool = Query(True),
    limit: int = Query(5)  # 预览前5题
):
    """预览导出内容"""
    db = next(get_db())
    
    subject = db.query(Subject).filter(
        Subject.id == subject_id
    ).first()
    
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    
    # 查询题目
    query = db.query(Question).filter(
        Question.subject_id == subject_id,
        Question.deleted_at.is_(None),
        Question.type.in_(get_supported_types())
    )
    
    questions = query.limit(limit).all()
    
    # 格式化题目
    question_list = []
    for q in questions:
        question_dict = {
            'id': q.id,
            'type': q.type,
            'content': q.content,
            'options': q.options if q.options else {},
            'answer': q.answer if include_answer else '',
            'analysis': q.explanation if include_analysis else ''
        }
        question_list.append(question_dict)
    
    return {
        'subject_name': subject.name,
        'preview_questions': question_list,
        'total_count': query.count()
    }


@router.get("/download")
def export_questions(
    subject_id: int = Query(...),
    format: str = Query("word"),
    include_answer: bool = Query(True),
    include_analysis: bool = Query(True),
    question_ids: Optional[str] = Query(None),  # 逗号分隔的题目ID或题目类型
    question_types: Optional[str] = Query(None)  # 逗号分隔的题目类型
):
    """导出题目并返回文件"""
    db = next(get_db())
    
    subject = db.query(Subject).filter(
        Subject.id == subject_id
    ).first()
    
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    
    # 查询题目
    query = db.query(Question).filter(
        Question.subject_id == subject_id,
        Question.deleted_at.is_(None),
        Question.type.in_(get_supported_types())
    )
    
    # 解析题目类型过滤
    if question_types:
        try:
            types = [x.strip() for x in question_types.split(',') if x.strip()]
            if types:
                query = query.filter(Question.type.in_(types))
        except ValueError:
            pass
    
    # 解析题目ID列表（如果提供）
    if question_ids:
        try:
            selected_ids = [int(x.strip()) for x in question_ids.split(',') if x.strip()]
            if selected_ids:
                query = query.filter(Question.id.in_(selected_ids))
        except ValueError:
            pass
    
    questions = query.all()
    
    if not questions:
        raise HTTPException(status_code=400, detail="没有可导出的题目")
    
    # 格式化题目
    question_list = []
    for q in questions:
        question_dict = {
            'id': q.id,
            'type': q.type,
            'content': q.content,
            'options': q.options if q.options else {},
            'answer': q.answer if include_answer else '',
            'analysis': q.explanation if include_analysis else ''
        }
        question_list.append(question_dict)
    
    # 生成文件名
    safe_subject_name = "".join(c for c in subject.name if c.isalnum() or c in (' ', '-', '_')).strip()
    
    # 导出文件
    if format == "pdf":
        filepath = export_to_pdf(
            question_list,
            safe_subject_name,
            include_answer,
            include_analysis
        )
        media_type = "application/pdf"
    else:
        # 默认导出 Word
        filepath = export_to_word(
            question_list,
            safe_subject_name,
            include_answer,
            include_analysis
        )
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    
    # 返回文件
    filename = os.path.basename(filepath)
    
    return FileResponse(
        filepath,
        media_type=media_type,
        filename=filename
    )


@router.get("/formats")
def get_formats():
    """获取支持的导出格式"""
    return [
        {"value": "word", "label": "Word 文档 (.docx)"},
        {"value": "pdf", "label": "PDF 文档 (.pdf)"}
    ]


@router.get("/types")
def get_question_types():
    """获取支持的题目类型"""
    type_info = {
        'single': {'label': '单选题', 'has_options': True},
        'multiple': {'label': '多选题', 'has_options': True},
        'judge': {'label': '判断题', 'has_options': False},
        'fill': {'label': '填空题', 'has_options': False},
        'short_answer': {'label': '简答题', 'has_options': False}
    }
    
    return [
        {'value': key, **value}
        for key, value in type_info.items()
    ]
