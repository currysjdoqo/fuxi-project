from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Folder, Question, Subject, User, WrongQuestion

router = APIRouter(prefix="/folders", tags=["folders"])


# ---------- schemas ----------

class FolderCreate(BaseModel):
    name: str


class FolderUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None


class FolderOut(BaseModel):
    id: int
    name: str
    subject_count: int = 0
    question_count: int = 0
    created_at: str | None = None


class SubjectWithFolder(BaseModel):
    """带子 folder 信息的 subject 简略，给前端按 folder 分组用。"""

    id: int
    name: str
    folder_id: int | None = None
    folder_name: str | None = None
    question_count: int = 0
    wrong_count: int = 0
    created_at: str | None = None


class FolderWithSubjects(FolderOut):
    subjects: list[SubjectWithFolder] = []


# ---------- helpers ----------

def _folder_aggregates(db: Session, user_id: int):
    """一次算出每个 folder 的科目数与题目数。"""
    subject_counts = dict(
        db.query(Subject.folder_id, func.count(Subject.id))
        .filter(Subject.user_id == user_id)
        .group_by(Subject.folder_id)
        .all()
    )
    question_counts = dict(
        db.query(Subject.folder_id, func.count(Question.id))
        .join(Subject, Subject.id == Question.subject_id)
        .filter(Subject.user_id == user_id, Question.deleted_at.is_(None))
        .group_by(Subject.folder_id)
        .all()
    )
    return subject_counts, question_counts


def _subject_aggregates(db: Session, subject_ids: list[int]):
    """一次算出这批科目的题目数与错题数。"""
    if not subject_ids:
        return {}, {}
    question_counts = dict(
        db.query(Question.subject_id, func.count(Question.id))
        .filter(Question.subject_id.in_(subject_ids), Question.deleted_at.is_(None))
        .group_by(Question.subject_id)
        .all()
    )
    wrong_counts = dict(
        db.query(Question.subject_id, func.count(WrongQuestion.id))
        .join(WrongQuestion, WrongQuestion.question_id == Question.id)
        .filter(Question.subject_id.in_(subject_ids))
        .group_by(Question.subject_id)
        .all()
    )
    return question_counts, wrong_counts


def _subject_payload(subject: Subject, folder_cache, question_counts, wrong_counts) -> dict:
    return {
        "id": subject.id,
        "name": subject.name,
        "folder_id": subject.folder_id,
        "folder_name": folder_cache.get(subject.folder_id),
        "question_count": question_counts.get(subject.id, 0),
        "wrong_count": wrong_counts.get(subject.id, 0),
        "created_at": subject.created_at.isoformat() if subject.created_at else None,
    }


def _to_folder_out(db: Session, folder: Folder) -> dict:
    subject_counts, question_counts = _folder_aggregates(db, folder.user_id)
    return {
        "id": folder.id,
        "name": folder.name,
        "subject_count": subject_counts.get(folder.id, 0),
        "question_count": question_counts.get(folder.id, 0),
        "created_at": folder.created_at.isoformat() if folder.created_at else None,
    }


# ---------- endpoints ----------

@router.get("", response_model=list[FolderOut])
def list_folders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    folders = (
        db.query(Folder)
        .filter(Folder.user_id == current_user.id)
        .order_by(Folder.sort_order.asc(), Folder.id.asc())
        .all()
    )
    subject_counts, question_counts = _folder_aggregates(db, current_user.id)
    return [
        {
            "id": f.id,
            "name": f.name,
            "subject_count": subject_counts.get(f.id, 0),
            "question_count": question_counts.get(f.id, 0),
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in folders
    ]


@router.get("/with-subjects", response_model=list[FolderWithSubjects])
def list_folders_with_subjects(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """每个 folder 下带上它的 subjects；另外返回一个 key 为 null 的"未分类"桶。

    所有统计都用 group by 一次算完，避免按 folder / subject 逐个发 count 查询。
    """
    folders = (
        db.query(Folder)
        .filter(Folder.user_id == current_user.id)
        .order_by(Folder.sort_order.asc(), Folder.id.asc())
        .all()
    )
    subjects = (
        db.query(Subject)
        .filter(Subject.user_id == current_user.id)
        .order_by(Subject.folder_id.asc().nullslast(), Subject.id.asc())
        .all()
    )

    folder_cache: dict[int | None, str | None] = {f.id: f.name for f in folders}
    subject_question_counts, subject_wrong_counts = _subject_aggregates(db, [s.id for s in subjects])
    folder_subject_counts, folder_question_counts = _folder_aggregates(db, current_user.id)

    groups: dict[int | None, list[Subject]] = {}
    for s in subjects:
        groups.setdefault(s.folder_id, []).append(s)

    def payload(folder: Folder, subs: list[Subject]) -> dict:
        return {
            "id": folder.id,
            "name": folder.name,
            "subject_count": folder_subject_counts.get(folder.id, 0),
            "question_count": folder_question_counts.get(folder.id, 0),
            "created_at": folder.created_at.isoformat() if folder.created_at else None,
            "subjects": [
                _subject_payload(s, folder_cache, subject_question_counts, subject_wrong_counts) for s in subs
            ],
        }

    result: list[FolderWithSubjects] = [payload(f, groups.get(f.id, [])) for f in folders]

    # 未分类 bucket（有科目但没 folder 的）
    uncategorized = groups.get(None, [])
    if uncategorized:
        result.append(
            {
                "id": -1,
                "name": "未分类科目",
                "subject_count": len(uncategorized),
                "question_count": sum(subject_question_counts.get(s.id, 0) for s in uncategorized),
                "created_at": None,
                "subjects": [
                    _subject_payload(s, folder_cache, subject_question_counts, subject_wrong_counts)
                    for s in uncategorized
                ],
            }
        )

    return result


@router.post("", response_model=FolderOut)
def create_folder(
    req: FolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="文件夹名称不能为空")
    existing = db.query(Folder).filter(Folder.user_id == current_user.id, Folder.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="文件夹已存在")
    folder = Folder(user_id=current_user.id, name=name)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return _to_folder_out(db, folder)


@router.patch("/{folder_id}", response_model=FolderOut)
def update_folder(
    folder_id: int,
    req: FolderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == current_user.id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    if req.name is not None:
        folder.name = req.name.strip()
    if req.sort_order is not None:
        folder.sort_order = req.sort_order
    db.commit()
    db.refresh(folder)
    return _to_folder_out(db, folder)


@router.delete("/{folder_id}")
def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == current_user.id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    # 把该 folder 下的 subject 置为未分类，不删 subject
    db.query(Subject).filter(Subject.folder_id == folder.id).update({"folder_id": None})
    db.delete(folder)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{folder_id}/subjects/{subject_id}")
def add_subject_to_folder(
    folder_id: int,
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    folder = db.query(Folder).filter(Folder.id == folder_id, Folder.user_id == current_user.id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    subject = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == current_user.id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    subject.folder_id = folder.id
    db.commit()
    return {"message": "已加入文件夹"}


@router.delete("/{folder_id}/subjects/{subject_id}")
def remove_subject_from_folder(
    folder_id: int,
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    subject = db.query(Subject).filter(Subject.id == subject_id, Subject.user_id == current_user.id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    subject.folder_id = None
    db.commit()
    return {"message": "已移出文件夹"}
