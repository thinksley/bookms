from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book, BorrowRecord, User
from app.schemas import BookOut, StatsOut
from app.security import get_current_user

router = APIRouter(prefix="/api/stats", tags=["数据看板"], dependencies=[Depends(get_current_user)])

LOW_STOCK_THRESHOLD = 3


@router.get("", response_model=StatsOut)
def stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    titles = db.query(Book).count()
    stock = db.query(func.coalesce(func.sum(Book.stock), 0)).scalar()

    active = db.query(BorrowRecord).filter(BorrowRecord.status == "在借").count()
    overdue = (
        db.query(BorrowRecord)
        .filter(BorrowRecord.status == "在借", BorrowRecord.due_date < date.today())
        .count()
    )

    categories = (
        db.query(Book.category, func.count(Book.id).label("count"))
        .filter(Book.category.isnot(None))
        .group_by(Book.category)
        .order_by(func.count(Book.id).desc())
        .all()
    )
    top_borrowed = (
        db.query(BorrowRecord.book_title, func.count(BorrowRecord.id).label("count"))
        .group_by(BorrowRecord.book_title)
        .order_by(func.count(BorrowRecord.id).desc())
        .limit(5)
        .all()
    )
    low_stock = (
        db.query(Book)
        .filter(Book.stock <= LOW_STOCK_THRESHOLD)
        .order_by(Book.stock.asc(), Book.id.desc())
        .limit(5)
        .all()
    )
    recent = db.query(Book).order_by(Book.id.desc()).limit(5).all()

    # ---- 借阅热力图（近 12 个月 × 星期）----
    # 记录量不大，取日期列表回 Python 里数，避开各数据库 SQL 方言差异
    borrow_dates = [row[0] for row in db.query(BorrowRecord.borrow_date).all()]

    # 从 11 个月前推到本月，生成 12 个月标签（旧 → 新）
    today = date.today()
    cursor = date(today.year, today.month, 1)
    months = []
    for _ in range(12):
        months.append(f"{cursor.year}-{cursor.month:02d}")
        cursor = date(cursor.year - 1, cursor.month, 1) if cursor.month == 1 else date(cursor.year, cursor.month - 1, 1)
    months.reverse()

    month_index = {m: i for i, m in enumerate(months)}
    monthly_counts = [0] * len(months)
    weekday_counts = [0] * 7  # weekday(): 周一=0 … 周日=6
    heatmap = [[0] * len(months) for _ in range(7)]  # 行=星期，列=月份

    for bd in borrow_dates:
        if bd is None:
            continue
        weekday_counts[bd.weekday()] += 1
        idx = month_index.get(f"{bd.year}-{bd.month:02d}")
        if idx is not None:
            monthly_counts[idx] += 1
            heatmap[bd.weekday()][idx] += 1

    return {
        "titles": titles,
        "stock": stock,
        "active_borrows": active,
        "overdue": overdue,
        "categories": [{"name": name, "count": count} for name, count in categories],
        "top_borrowed": [{"title": title, "count": count} for title, count in top_borrowed],
        "low_stock": [{"id": b.id, "title": b.title, "stock": b.stock} for b in low_stock],
        "recent": recent,
        "monthly_borrows": [{"month": m, "count": c} for m, c in zip(months, monthly_counts)],
        "weekday_borrows": weekday_counts,
        "heatmap": heatmap,
    }
