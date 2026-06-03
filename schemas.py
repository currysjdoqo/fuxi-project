from pydantic import BaseModel
from datetime import datetime
from typing import Any, Dict, Optional


class SubjectOut(BaseModel):
    id: int
    name: str
    question_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionCreate(BaseModel):
    """
    创建题目时使用的 Pydantic 模型
    用于接收客户端提交的题目数据
    """
    # 题型（如：单选题、多选题等）
    type: str

    # 科目/分类 ID
    subject_id: Optional[int] = None
    
    # 题干内容
    content: str
    
    # 选项，字典格式 {"A": "选项A内容", "B": "选项B内容", ...}
    options: Dict[str, Any]
    
    # 正确答案（单个字母，如：A、B、C、D）
    answer: str
    
    # 答案解析（可选）
    explanation: Optional[str] = None


class QuestionOut(BaseModel):
    """
    返回题目信息时使用的 Pydantic 模型
    用于序列化数据库查询结果返回给客户端
    """
    # 题目 ID
    id: int

    # 科目/分类 ID
    subject_id: Optional[int] = None
    
    # 题型：single / judge / fill / short
    type: str
    
    # 题干内容
    content: str
    
    # 选项
    options: Dict[str, Any]
    
    # 正确答案
    answer: str
    
    # 答案解析（可选）
    explanation: Optional[str] = None

    # 是否重点题
    is_important: int = 0
    
    # 创建时间
    created_at: datetime

    class Config:
        """
        配置类：允许从 ORM 模型直接转换
        """
        from_attributes = True
