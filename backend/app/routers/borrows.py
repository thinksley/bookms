from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book, BorrowRecord, Reader, User
from app.routers.settings import get_rules
from app.schemas import BorrowCreate, BorrowOut, BorrowPage
from app.security import get_current_user

MAX_RENEWS = 1  # 每笔借阅限续借次数

router = APIRouter(
    prefix="/api/borrows",
    tags=["借阅管理"],
    dependencies=[Depends(get_current_user)],
)


def to_out(record: BorrowRecord) -> BorrowOut:
    out = BorrowOut.model_validate(record)
    out.status = record.display_status  # 逾期为动态判定
    return out


@router.get("", response_model=BorrowPage)
def list_borrows(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),  # 在借 / 逾期 / 已还
    keyword: Optional[str] = None,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(BorrowRecord)
    if status == "逾期":
        query = query.filter(BorrowRecord.status == "在借", BorrowRecord.due_date < date.today())
    elif status:
        query = query.filter(BorrowRecord.status == status)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(BorrowRecord.book_title.like(like), BorrowRecord.borrower_name.like(like))
        )
    total = query.count()
    records = query.order_by(BorrowRecord.id.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "items": [to_out(r) for r in records]}


@router.post("", response_model=BorrowOut, status_code=201)
def borrow_book(
    data: BorrowCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    book = db.query(Book).filter(Book.id == data.book_id, Book.deleted_at.is_(None)).first()
    if not book:
        raise HTTPException(status_code=404, detail="图书不存在")
    if book.stock <= 0:
        raise HTTPException(status_code=400, detail="库存不足，无法借出")

    reader = db.query(Reader).filter(Reader.id == data.reader_id).first()
    if not reader:
        raise HTTPException(status_code=404, detail="读者不存在")
    active = (
        db.query(BorrowRecord)
        .filter(BorrowRecord.reader_id == reader.id, BorrowRecord.status == "在借")
        .count()
    )
    if active >= reader.max_borrow:
        raise HTTPException(
            status_code=400,
            detail=f"「{reader.name}」在借 {active} 本，已达可借上限 {reader.max_borrow} 本",
        )

    rules = get_rules(db)
    days = data.days if data.days is not None else rules["borrow_days"]

    today = date.today()
    record = BorrowRecord(
        book_id=book.id,
        book_title=book.title,
        reader_id=reader.id,
        borrower_name=reader.name,
        borrow_date=today,
        due_date=today + timedelta(days=days),
        status="在借",
        operator=current_user.username,
        remark=data.remark,
    )
    book.stock -= 1
    db.add(record)
    db.commit()
    db.refresh(record)
    return to_out(record)


@router.post("/{record_id}/return", response_model=BorrowOut)
def return_book(
    record_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(BorrowRecord).filter(BorrowRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="借阅记录不存在")
    if record.status != "在借":
        raise HTTPException(status_code=400, detail="该记录已归还")

    record.return_date = date.today()
    record.status = "已还"
    if record.book_id:
        book = db.query(Book).filter(Book.id == record.book_id).first()
        if book:
            book.stock += 1
    db.commit()
    db.refresh(record)
    return to_out(record)


@router.post("/{record_id}/renew", response_model=BorrowOut)
def renew_record(
    record_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(BorrowRecord).filter(BorrowRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="借阅记录不存在")
    if record.status != "在借":
        raise HTTPException(status_code=400, detail="已归还的记录不能续借")
    if record.renewed_count >= MAX_RENEWS:
        raise HTTPException(status_code=400, detail="每笔借阅限续借一次")

    # 逾期后也允许续借，从今天起算
    base = max(date.today(), record.due_date) if record.due_date else date.today()
    record.due_date = base + timedelta(days=get_rules(db)["renew_days"])
    record.renewed_count += 1
    db.commit()
    db.refresh(record)
    return to_out(record)


@router.delete("/{record_id}", status_code=204)
def delete_record(
    record_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(BorrowRecord).filter(BorrowRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="借阅记录不存在")
    # 在借记录被删除视为取消借阅，恢复库存
    if record.status == "在借" and record.book_id:
        book = db.query(Book).filter(Book.id == record.book_id).first()
        if book:
            book.stock += 1
    db.delete(record)
    db.commit()
    return None
