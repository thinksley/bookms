from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BorrowRecord, Reader, User
from app.routers.settings import get_rules
from app.schemas import ReaderCreate, ReaderOut, ReaderPage, ReaderUpdate
from app.security import get_current_user

router = APIRouter(
    prefix="/api/readers",
    tags=["读者管理"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=ReaderPage)
def list_readers(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    keyword: Optional[str] = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Reader)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(Reader.name.like(like), Reader.card_no.like(like), Reader.phone.like(like))
        )
    total = query.count()
    readers = query.order_by(Reader.id.desc()).offset((page - 1) * size).limit(size).all()

    active = dict(
        db.query(BorrowRecord.reader_id, func.count(BorrowRecord.id))
        .filter(BorrowRecord.status == "在借", BorrowRecord.reader_id.isnot(None))
        .group_by(BorrowRecord.reader_id)
        .all()
    )
    items = []
    for r in readers:
        item = ReaderOut.model_validate(r)
        item.active_borrows = active.get(r.id, 0)
        items.append(item)
    return {"total": total, "items": items}


@router.post("", response_model=ReaderOut, status_code=201)
def create_reader(
    data: ReaderCreate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.card_no and db.query(Reader).filter(Reader.card_no == data.card_no).first():
        raise HTTPException(status_code=400, detail="该读者证号已存在")
    values = data.model_dump()
    if values.get("max_borrow") is None:  # 未指定时用系统设置里的默认上限
        values["max_borrow"] = get_rules(db)["max_borrow"]
    reader = Reader(**values)
    db.add(reader)
    db.commit()
    db.refresh(reader)
    if not reader.card_no:
        reader.card_no = f"R{reader.id:04d}"  # 未填证号时自动生成
        db.commit()
        db.refresh(reader)
    return reader


@router.put("/{reader_id}", response_model=ReaderOut)
def update_reader(
    reader_id: int,
    data: ReaderUpdate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reader = db.query(Reader).filter(Reader.id == reader_id).first()
    if not reader:
        raise HTTPException(status_code=404, detail="读者不存在")
    updates = data.model_dump(exclude_unset=True)

    new_card = updates.get("card_no")
    if new_card and new_card != reader.card_no:
        if db.query(Reader).filter(Reader.card_no == new_card, Reader.id != reader_id).first():
            raise HTTPException(status_code=400, detail="该读者证号已存在")

    for field, value in updates.items():
        setattr(reader, field, value)
    db.commit()
    db.refresh(reader)
    return reader


@router.delete("/{reader_id}", status_code=204)
def delete_reader(
    reader_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reader = db.query(Reader).filter(Reader.id == reader_id).first()
    if not reader:
        raise HTTPException(status_code=404, detail="读者不存在")
    active = (
        db.query(BorrowRecord)
        .filter(BorrowRecord.reader_id == reader_id, BorrowRecord.status == "在借")
        .count()
    )
    if active:
        raise HTTPException(status_code=400, detail=f"该读者有 {active} 条在借记录，请先归还")
    db.delete(reader)  # 历史借阅记录保留（读者名快照）
    db.commit()
    return None
