from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from datetime import datetime
from database import Base


class Subject(Base):
    """
    科目/分类模型
    例如：机器学习、数据结构、操作系统
    """
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Question(Base):
    """
    题目模型
    存储单选题的相关信息
    """
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), index=True, nullable=True)
    type = Column(String, index=True)
    content = Column(String, index=True)
    options = Column(JSON)
    answer = Column(String)
    explanation = Column(String)
    is_important = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)


class PracticeRecord(Base):
    """
    练习记录模型
    记录用户做题的历史记录
    """
    __tablename__ = "practice_records"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    user_answer = Column(String, nullable=False)
    is_correct = Column(Integer, nullable=False)
    practiced_at = Column(DateTime, default=datetime.utcnow)


class WrongQuestion(Base):
    """
    错题本模型
    记录用户做错的题目，用于复习
    """
    __tablename__ = "wrong_questions"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, unique=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    review_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    last_reviewed_at = Column(DateTime)
