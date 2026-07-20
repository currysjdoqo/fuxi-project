from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    token = Column(String, unique=True, index=True, nullable=True)
    avatar = Column(String, nullable=True)
    signature = Column(String, nullable=True)
    user_code = Column(String(10), unique=True, index=True, nullable=True)
    invite_code = Column(String(16), unique=True, index=True, nullable=True)
    invited_by_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    ai_provider = Column(String, default="platform")
    custom_ai_api_key_encrypted = Column(String, nullable=True)
    balance_cents = Column(Integer, default=0)
    call_credits = Column(Integer, default=0)
    member_expires_at = Column(DateTime, nullable=True)
    member_calls_remaining = Column(Integer, default=0)
    free_calls_used = Column(Integer, default=0)
    free_calls_date = Column(String, nullable=True)
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


class Friendship(Base):
    __tablename__ = "friendships"
    __table_args__ = (
        UniqueConstraint("user_id", "friend_id", name="uq_friendship"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    friend_id = Column(Integer, ForeignKey("users.id"), index=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), index=True)
    receiver_id = Column(Integer, ForeignKey("users.id"), index=True)
    content = Column(String, nullable=False)
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ShareRecord(Base):
    __tablename__ = "share_records"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), index=True)
    to_user_id = Column(Integer, ForeignKey("users.id"), index=True)
    accepted = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    source_user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    amount_cents = Column(Integer, nullable=False)
    tx_type = Column(String, nullable=False)
    note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class KeepSeekUsage(Base):
    __tablename__ = "keepseek_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    source = Column(String, nullable=False)
    cost_type = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
