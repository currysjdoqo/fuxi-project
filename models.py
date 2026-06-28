from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    token = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    name = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
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
    __tablename__ = "practice_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    user_answer = Column(String, nullable=False)
    is_correct = Column(Integer, nullable=False)
    practiced_at = Column(DateTime, default=datetime.utcnow)


class WrongQuestion(Base):
    __tablename__ = "wrong_questions"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_wrong_questions_user_question"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    added_at = Column(DateTime, default=datetime.utcnow)
    review_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    last_reviewed_at = Column(DateTime)


class PlanItem(Base):
    __tablename__ = "plan_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    date = Column(String, index=True, nullable=False)
    content = Column(String, nullable=False)
    completed = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
