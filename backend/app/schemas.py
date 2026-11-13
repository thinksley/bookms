from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BookBase(BaseModel):
    # ---- 基本信息 ----
    title: str = Field(..., max_length=200)
    subtitle: Optional[str] = Field(None, max_length=200)
    original_title: Optional[str] = Field(None, max_length=200)
    author: str = Field(..., max_length=100)
    translator: Optional[str] = Field(None, max_length=100)
    isbn: Optional[str] = Field(None, max_length=20)
    series: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=50)
    # ---- 出版信息 ----
    publisher: Optional[str] = Field(None, max_length=100)
    publish_place: Optional[str] = Field(None, max_length=100)
    publish_date: Optional[date] = None
    edition: Optional[str] = Field(None, max_length=50)
    binding: Optional[str] = Field(None, max_length=20)
    book_format: Optional[str] = Field(None, max_length=20)
    page_count: Optional[int] = Field(None, ge=0)
    price: float = Field(0, ge=0)
    # ---- 分类与内容 ----
    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[str] = Field(None, max_length=200)
    summary: Optional[str] = None
    author_intro: Optional[str] = None
    catalog: Optional[str] = None
    # ---- 馆藏信息 ----
    barcode: Optional[str] = Field(None, max_length=50)
    call_number: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=100)
    source: Optional[str] = Field(None, max_length=50)
    cover_url: Optional[str] = Field(None, max_length=500)
    stock: int = Field(0, ge=0)


class BookCreate(BookBase):
    pass


class BookUpdate(BookBase):
    # 全部字段可缺省：仅更新传入的字段
    title: Optional[str] = Field(None, max_length=200)
    author: Optional[str] = Field(None, max_length=100)
    price: Optional[float] = Field(None, ge=0)
    stock: Optional[int] = Field(None, ge=0)


class BookOut(BookBase):
    id: int
    created_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BookPage(BaseModel):
    total: int
    items: list[BookOut]


# ---------- 用户管理 ----------

class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=72)
    is_admin: bool = False


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=2, max_length=50)
    password: Optional[str] = Field(None, min_length=6, max_length=72)
    is_admin: Optional[bool] = None


class UserPage(BaseModel):
    total: int
    items: list[UserOut]


# ---------- 借阅管理 ----------

class BorrowCreate(BaseModel):
    book_id: int
    reader_id: int
    days: Optional[int] = Field(None, ge=1, le=365)  # 不传 = 用系统设置里的默认借期
    remark: Optional[str] = Field(None, max_length=200)


class BorrowOut(BaseModel):
    id: int
    book_id: Optional[int] = None
    book_title: str
    reader_id: Optional[int] = None
    borrower_name: str
    borrow_date: Optional[date] = None
    due_date: Optional[date] = None
    return_date: Optional[date] = None
    status: str
    renewed_count: int = 0
    operator: Optional[str] = None
    remark: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BorrowPage(BaseModel):
    total: int
    items: list[BorrowOut]


# ---------- 读者管理 ----------

class ReaderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    card_no: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    max_borrow: Optional[int] = Field(None, ge=1, le=20)  # 不传 = 用系统设置里的默认上限
    remark: Optional[str] = Field(None, max_length=200)


class ReaderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    card_no: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    max_borrow: Optional[int] = Field(None, ge=1, le=20)
    remark: Optional[str] = Field(None, max_length=200)


class ReaderOut(BaseModel):
    id: int
    card_no: Optional[str] = None
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    max_borrow: int
    remark: Optional[str] = None
    created_at: Optional[datetime] = None
    active_borrows: int = 0

    model_config = ConfigDict(from_attributes=True)


class ReaderPage(BaseModel):
    total: int
    items: list[ReaderOut]


# ---------- 修改密码 ----------

class PasswordChange(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=72)


# ---------- 分类字典 ----------

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class CategoryOut(BaseModel):
    id: int
    name: str
    book_count: int = 0
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------- 图书批量操作 ----------

class BookBatchIds(BaseModel):
    ids: list[int] = Field(..., min_length=1)


class BookBatchCategory(BookBatchIds):
    category: str = Field(..., min_length=1, max_length=50)


# ---------- 数据看板 ----------

class CategoryStat(BaseModel):
    name: str
    count: int


class TopBorrowed(BaseModel):
    title: str
    count: int


class LowStockBook(BaseModel):
    id: int
    title: str
    stock: int


class MonthCount(BaseModel):
    month: str  # "2026-01"
    count: int


class StatsOut(BaseModel):
    titles: int
    stock: int
    active_borrows: int
    overdue: int
    categories: list[CategoryStat]
    top_borrowed: list[TopBorrowed]
    low_stock: list[LowStockBook]
    recent: list[BookOut]
    monthly_borrows: list[MonthCount]  # 近 12 个月每月借阅量
    weekday_borrows: list[int]  # 周一~周日各借了多少次
    heatmap: list[list[int]]  # 7 行(星期) × 12 列(月份) 的热力矩阵


# ---------- 系统设置 ----------

class SettingsOut(BaseModel):
    borrow_days: int  # 默认借期（天）
    renew_days: int  # 续借顺延天数
    fine_per_day: float  # 逾期日罚金（元），为罚款功能预留
    max_borrow: int  # 新读者默认可借上限


class SettingsUpdate(BaseModel):
    # 全部可缺省：仅更新传入的项
    borrow_days: Optional[int] = Field(None, ge=1, le=365)
    renew_days: Optional[int] = Field(None, ge=1, le=365)
    fine_per_day: Optional[float] = Field(None, ge=0, le=100)
    max_borrow: Optional[int] = Field(None, ge=1, le=20)
