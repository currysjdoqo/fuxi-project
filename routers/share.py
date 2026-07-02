from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Friendship, Question, ShareRecord, Subject, User

router = APIRouter()


class ShareSubjectRequest(BaseModel):
    subject_id: int
    friend_id: int


def build_shared_subject_name(db: Session, user_id: int, base_name: str) -> str:
    existing_names = {
        name for (name,) in db.query(Subject.name).filter(Subject.user_id == user_id).all()
    }
    if base_name not in existing_names:
        return base_name

    index = 2
    while True:
        candidate = f"{base_name} (分享 {index})"
        if candidate not in existing_names:
            return candidate
        index += 1


@router.post("/share/subject")
def share_subject(
    request: ShareSubjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subject = db.query(Subject).filter(
        Subject.id == request.subject_id,
        Subject.user_id == current_user.id,
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="习题集不存在")

    if request.friend_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能分享给自己")

    is_friend = db.query(Friendship).filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == request.friend_id))
        | ((Friendship.user_id == request.friend_id) & (Friendship.friend_id == current_user.id)),
        Friendship.status == "accepted",
    ).first()
    if not is_friend:
        raise HTTPException(status_code=400, detail="对方不是你的好友")

    existing = db.query(ShareRecord).filter(
        ShareRecord.subject_id == request.subject_id,
        ShareRecord.from_user_id == current_user.id,
        ShareRecord.to_user_id == request.friend_id,
    ).first()
    if existing:
        if existing.accepted == 1:
            raise HTTPException(status_code=400, detail="该习题集已经分享过")
        existing.accepted = 0
        existing.created_at = datetime.utcnow()
        db.commit()
        return {"message": "分享请求已发送"}

    share_record = ShareRecord(
        subject_id=request.subject_id,
        from_user_id=current_user.id,
        to_user_id=request.friend_id,
    )
    db.add(share_record)
    db.commit()

    return {"message": "分享请求已发送"}


@router.get("/share/list")
def get_share_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    shares = db.query(ShareRecord).filter(
        ShareRecord.to_user_id == current_user.id
    ).order_by(ShareRecord.created_at.desc()).all()

    result = []
    for share in shares:
        subject = db.query(Subject).filter(Subject.id == share.subject_id).first()
        from_user = db.query(User).filter(User.id == share.from_user_id).first()
        if not subject or not from_user:
            continue

        question_count = db.query(Question).filter(
            Question.subject_id == subject.id,
            Question.user_id == share.from_user_id,
            Question.deleted_at.is_(None),
        ).count()
        result.append({
            "share_id": share.id,
            "subject_id": subject.id,
            "subject_name": subject.name,
            "question_count": question_count,
            "from_user_id": from_user.id,
            "from_username": from_user.username,
            "from_user_avatar": from_user.avatar,
            "accepted": share.accepted,
            "created_at": share.created_at.isoformat(),
        })

    return {"shares": result}


@router.post("/share/accept/{share_id}")
def accept_share(
    share_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    share = db.query(ShareRecord).filter(
        ShareRecord.id == share_id,
        ShareRecord.to_user_id == current_user.id,
        ShareRecord.accepted == 0,
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="分享请求不存在")

    subject = db.query(Subject).filter(Subject.id == share.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="习题集不存在")

    questions = db.query(Question).filter(
        Question.subject_id == subject.id,
        Question.user_id == share.from_user_id,
        Question.deleted_at.is_(None),
    ).all()

    new_subject = Subject(
        user_id=current_user.id,
        name=build_shared_subject_name(db, current_user.id, subject.name),
    )
    db.add(new_subject)
    db.commit()
    db.refresh(new_subject)

    if questions:
        db.add_all([
            Question(
                user_id=current_user.id,
                subject_id=new_subject.id,
                type=question.type,
                content=question.content,
                options=question.options,
                answer=question.answer,
                explanation=question.explanation,
                is_important=question.is_important,
            )
            for question in questions
        ])

    share.accepted = 1
    db.commit()

    return {
        "message": "已接受分享",
        "new_subject_id": new_subject.id,
        "question_count": len(questions),
    }


@router.post("/share/reject/{share_id}")
def reject_share(
    share_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    share = db.query(ShareRecord).filter(
        ShareRecord.id == share_id,
        ShareRecord.to_user_id == current_user.id,
        ShareRecord.accepted == 0,
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="分享请求不存在")

    db.delete(share)
    db.commit()

    return {"message": "已拒绝分享"}
