from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book, Category, User
from app.schemas import CategoryCreate, CategoryOut
from app.security import get_current_user

router = APIRouter(
    prefix="/api/categories",
    tags=["分类管理"],
    dependencies=[Depends(get_current_user)],
)


def ensure_category(db: Session, name: str) -> None:
    """图书保存时自动把新分类登记进字典表，保证字典与数据同步。"""
    if not name:
        return
    exists = db.query(Category).filter(Category.name == name).first()
    if not exists:
        db.add(Category(name=name))
        db.commit()


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    counts = dict(db.query(Book.category, func.count(Book.id)).group_by(Book.category).all())
    out = []
    for c in db.query(Category).order_by(Category.name).all():
        item = CategoryOut.model_validate(c)
        item.book_count = counts.get(c.name, 0)
        out.append(item)
    return out


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(
    data: CategoryCreate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if db.query(Category).filter(Category.name == data.name).first():
        raise HTTPException(status_code=400, detail="该分类已存在")
    category = Category(name=data.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryOut)
def rename_category(
    category_id: int,
    data: CategoryCreate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    name = data.name.strip()
    if name == category.name:
        return category
    if db.query(Category).filter(Category.name == name).first():
        raise HTTPException(status_code=400, detail="该分类已存在")

    old_name = category.name
    category.name = name
    # 同步更新图书上的分类值，保持字典与数据一致
    db.query(Book).filter(Book.category == old_name).update(
        {Book.category: name}, synchronize_session=False
    )
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(
    category_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    in_use = db.query(Book).filter(Book.category == category.name).count()
    if in_use:
        raise HTTPException(status_code=400, detail=f"有 {in_use} 本图书正在使用该分类，无法删除")
    db.delete(category)
    db.commit()
    return None
