from datetime import date, datetime
from io import BytesIO
from typing import Optional
from urllib.parse import quote
import json as _json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html import unescape as _unescape

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook, load_workbook
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book, BorrowRecord
from app.routers.categories import ensure_category
from app.schemas import (
    BookBatchCategory,
    BookBatchIds,
    BookCreate,
    BookOut,
    BookPage,
    BookUpdate,
)
from app.security import get_current_user

# 整个图书模块都需要登录
router = APIRouter(
    prefix="/api/books",
    tags=["图书管理"],
    dependencies=[Depends(get_current_user)],
)


def get_book_or_404(db: Session, book_id: int) -> Book:
    book = (
        db.query(Book)
        .filter(Book.id == book_id, Book.deleted_at.is_(None))
        .first()
    )
    if not book:
        raise HTTPException(status_code=404, detail="图书不存在")
    return book


@router.get("", response_model=BookPage)
def list_books(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Book).filter(Book.deleted_at.is_(None))
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(
                Book.title.like(like),
                Book.subtitle.like(like),
                Book.author.like(like),
                Book.translator.like(like),
                Book.isbn.like(like),
                Book.publisher.like(like),
                Book.category.like(like),
                Book.tags.like(like),
                Book.barcode.like(like),
                Book.call_number.like(like),
            )
        )
    total = query.count()
    items = query.order_by(Book.id.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "items": items}


# ---------- ISBN 在线查询 ----------

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _fetch_json(url: str, timeout: float = 6.0):
    req = urllib.request.Request(url, headers={"User-Agent": "bookms/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return _json.loads(resp.read().decode("utf-8"))


def _fetch_html(url: str, timeout: float = 6.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", _unescape(s or ""))).strip()


def _parse_date(s) -> Optional[str]:
    if not s:
        return None
    s = str(s).strip()
    m = re.match(r"(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2) or 1):02d}-{int(m.group(3) or 1):02d}"
    for fmt in ("%B %d, %Y",):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _run_with_timeout(fn, timeout: float):
    """单源限时执行；超时后线程留后台自行消亡，接口立刻换下一个源。"""
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(fn).result(timeout=timeout)
    finally:
        pool.shutdown(wait=False)


def _lookup_douban(isbn: str) -> Optional[dict]:
    """豆瓣图书页面（大陆网络首选源）：ISBN 短链自动跳转到详情页。"""
    html = _fetch_html(f"https://book.douban.com/isbn/{isbn}/", timeout=6.0)
    title_m = re.search(r'property="v:itemreviewed">([^<]+)', html)
    if not title_m:
        return None
    info_m = re.search(r'<div id="info">(.*?)</div>', html, re.S)
    info_html = info_m.group(1) if info_m else ""

    def field(label: str) -> Optional[str]:
        # 冒号位置不固定：可能在 span 内（出版社:</span>）也可能在外（ 作者</span>:）
        m = re.search(
            rf'<span class="pl">\s*{re.escape(label)}\s*:?\s*</span>\s*:?\s*(.*?)<br',
            info_html,
            re.S,
        )
        return _strip_tags(m.group(1)) if m else None

    def field_html(label: str) -> Optional[str]:
        m = re.search(
            rf'<span class="pl">\s*{re.escape(label)}\s*:?\s*</span>\s*:?\s*(.*?)<br',
            info_html,
            re.S,
        )
        return m.group(1).strip() if m else None

    cover = re.search(r'id="mainpic".*?src="(https://img\d+\.doubanio\.com[^"]+)"', html, re.S)
    cover_url = cover.group(1).replace("/s/public/", "/l/public/") if cover else None

    price_raw = field("定价") or ""
    price_m = re.search(r"[\d.]+", price_raw)
    intros = re.findall(r'<div class="intro">(.*?)</div>', html, re.S)
    summary = _strip_tags(intros[0])[:1000] if intros else None
    author_intro = _strip_tags(intros[1])[:1000] if len(intros) > 1 else None

    translator_html = field_html(" 译者")
    translator = ", ".join(re.findall(r">([^<>]+)</a>", translator_html)) or None if translator_html else None

    return {
        "title": title_m.group(1).strip(),
        "subtitle": field("副标题"),
        "original_title": field("原作名"),
        "author": field(" 作者"),
        "translator": translator,
        "publisher": field("出版社"),
        "publish_date": _parse_date(field("出版年")),
        "edition": field("版次"),
        "binding": field("装帧"),
        "series": field("丛书"),
        "page_count": int(field("页数") or 0) or None,
        "price": float(price_m.group(0)) if price_m else None,
        "category": None,
        "tags": None,
        "summary": summary,
        "author_intro": author_intro,
        "cover_url": cover_url,
        "language": None,
    }


def _lookup_openlibrary(isbn: str) -> Optional[dict]:
    d = _fetch_json(f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data")
    v = d.get(f"ISBN:{isbn}")
    if not v:
        return None
    notes = v.get("notes")
    if isinstance(notes, dict):
        notes = notes.get("value")
    return {
        "title": v.get("title"),
        "subtitle": v.get("subtitle"),
        "author": ", ".join(a.get("name", "") for a in v.get("authors", [])) or None,
        "publisher": (v.get("publishers") or [{}])[0].get("name"),
        "publish_date": _parse_date(v.get("publish_date")),
        "page_count": v.get("number_of_pages"),
        "summary": (notes or "")[:1000] or None,
        "cover_url": (v.get("cover") or {}).get("large") or (v.get("cover") or {}).get("medium"),
        "tags": ", ".join(s.get("name", "") for s in v.get("subjects", [])[:5]) or None,
        "category": None,
        "language": None,
    }


def _lookup_google(isbn: str) -> Optional[dict]:
    d = _fetch_json(f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}")
    items = d.get("items") or []
    if not items:
        return None
    v = items[0].get("volumeInfo") or {}
    image = (v.get("imageLinks") or {}).get("thumbnail") or ""
    return {
        "title": v.get("title"),
        "subtitle": v.get("subtitle"),
        "author": ", ".join(v.get("authors") or []) or None,
        "publisher": v.get("publisher"),
        "publish_date": _parse_date(v.get("publishedDate")),
        "page_count": v.get("pageCount"),
        "summary": (v.get("description") or "")[:1000] or None,
        "cover_url": image.replace("http://", "https://") or None,
        "tags": None,
        "category": (v.get("categories") or [None])[0],
        "language": v.get("language"),
    }


@router.get("/lookup")
def lookup_isbn(
    isbn: str = Query(..., min_length=8, max_length=20),
    _: None = Depends(get_current_user),
):
    isbn = isbn.strip()
    for fetch, source, seconds in (
        (_lookup_douban, "豆瓣", 6.0),
        (_lookup_openlibrary, "OpenLibrary", 4.0),
        (_lookup_google, "Google Books", 4.0),
    ):
        try:
            data = _run_with_timeout(lambda: fetch(isbn), timeout=seconds)
        except Exception:  # noqa: BLE001 单源失败/超时自动换下一个
            continue
        if data and data.get("title"):
            data["source"] = source
            return data
    raise HTTPException(status_code=502, detail="查询失败或未找到该书信息，请手动填写")


# ---------- 回收站（软删除） ----------

@router.get("/recycle-bin", response_model=list[BookOut])
def recycle_bin(db: Session = Depends(get_db), _: None = Depends(get_current_user)):
    return db.query(Book).filter(Book.deleted_at.isnot(None)).order_by(Book.deleted_at.desc()).all()


# ---------- Excel 导入导出 ----------

EXPORT_HEADERS = [
    "书名", "副标题", "原作名", "作者", "译者", "ISBN", "丛书系列", "语种",
    "出版社", "出版地", "出版日期", "版次", "装帧", "开本", "页数", "定价",
    "分类", "标签", "条形码", "索书号", "馆藏位置", "来源", "封面链接", "库存",
]
FIELD_MAP = {
    "书名": "title", "副标题": "subtitle", "原作名": "original_title",
    "作者": "author", "译者": "translator", "ISBN": "isbn",
    "丛书系列": "series", "语种": "language", "出版社": "publisher",
    "出版地": "publish_place", "出版日期": "publish_date", "版次": "edition",
    "装帧": "binding", "开本": "book_format", "页数": "page_count",
    "定价": "price", "分类": "category", "标签": "tags", "条形码": "barcode",
    "索书号": "call_number", "馆藏位置": "location", "来源": "source",
    "封面链接": "cover_url", "库存": "stock",
}


@router.get("/export")
def export_books(
    _: None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wb = Workbook()
    ws = wb.active
    ws.title = "图书数据"
    ws.append(EXPORT_HEADERS)
    for b in db.query(Book).order_by(Book.id).all():
        row = []
        for h in EXPORT_HEADERS:
            v = getattr(b, FIELD_MAP[h])
            if h == "出版日期":
                v = v.strftime("%Y-%m-%d") if v else None
            row.append(v)
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = quote(f"图书数据_{date.today().strftime('%Y%m%d')}.xlsx")
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


def _clean_str(v, limit: int):
    if v is None:
        return None
    s = str(v).strip()
    return s[:limit] or None


def _to_int(v):
    if v in (None, ""):
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def _to_float(v):
    if v in (None, ""):
        return 0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0


def _to_date(v):
    if isinstance(v, datetime):
        return v.date()
    if v is None or str(v).strip() == "":
        return None
    try:
        return datetime.strptime(str(v).strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


@router.post("/import")
def import_books(
    file: UploadFile = File(...),
    _: None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 文件")
    try:
        wb = load_workbook(BytesIO(file.file.read()), data_only=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Excel 文件解析失败")

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise HTTPException(status_code=400, detail="文件为空")

    header = [str(c).strip() if c is not None else "" for c in rows[0]]
    fields = [FIELD_MAP[h] for h in header if h in FIELD_MAP]
    if "title" not in fields or "author" not in fields:
        raise HTTPException(status_code=400, detail="表头缺少「书名」或「作者」列")

    created = skipped = failed = 0
    errors = []
    for i, row in enumerate(rows[1:], start=2):
        raw = {}
        for cell, h in zip(row, header):
            if h in FIELD_MAP:
                raw[FIELD_MAP[h]] = cell

        title = str(raw.get("title") or "").strip()
        author = str(raw.get("author") or "").strip()
        if not title or not author:
            failed += 1
            errors.append(f"第{i}行：书名和作者不能为空")
            continue

        isbn = _clean_str(raw.get("isbn"), 20)
        if isbn and db.query(Book).filter(Book.isbn == isbn).first():
            skipped += 1
            errors.append(f"第{i}行：ISBN {isbn} 已存在，跳过")
            continue

        payload = {
            "title": title[:200],
            "author": author[:100],
            "subtitle": _clean_str(raw.get("subtitle"), 200),
            "original_title": _clean_str(raw.get("original_title"), 200),
            "translator": _clean_str(raw.get("translator"), 100),
            "isbn": isbn,
            "series": _clean_str(raw.get("series"), 100),
            "language": _clean_str(raw.get("language"), 50) or "中文",
            "publisher": _clean_str(raw.get("publisher"), 100),
            "publish_place": _clean_str(raw.get("publish_place"), 100),
            "publish_date": _to_date(raw.get("publish_date")),
            "edition": _clean_str(raw.get("edition"), 50),
            "binding": _clean_str(raw.get("binding"), 20),
            "book_format": _clean_str(raw.get("book_format"), 20),
            "page_count": _to_int(raw.get("page_count")),
            "price": _to_float(raw.get("price")),
            "category": _clean_str(raw.get("category"), 50),
            "tags": _clean_str(raw.get("tags"), 200),
            "barcode": _clean_str(raw.get("barcode"), 50),
            "call_number": _clean_str(raw.get("call_number"), 100),
            "location": _clean_str(raw.get("location"), 100),
            "source": _clean_str(raw.get("source"), 50),
            "cover_url": _clean_str(raw.get("cover_url"), 500),
            "stock": _to_int(raw.get("stock")) or 0,
        }
        try:
            db.add(Book(**payload))
            if payload["category"]:
                ensure_category(db, payload["category"])
            db.commit()
            created += 1
        except Exception as e:  # noqa: BLE001 单行失败不影响整体导入
            db.rollback()
            failed += 1
            errors.append(f"第{i}行：写入失败（{e}）")

    return {
        "created": created,
        "skipped": skipped,
        "failed": failed,
        "errors": errors[:20],
        "error_total": len(errors),
    }


# ---------- 批量操作 ----------

@router.post("/batch-delete")
def batch_delete(
    data: BookBatchIds,
    _: None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    books = db.query(Book).filter(Book.id.in_(data.ids), Book.deleted_at.is_(None)).all()
    _ensure_no_active_borrow(db, books)
    for b in books:
        _soft_delete(b)
    db.commit()
    return {"deleted": len(books)}


@router.post("/batch-category")
def batch_category(
    data: BookBatchCategory,
    _: None = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.category:
        ensure_category(db, data.category)
    updated = (
        db.query(Book)
        .filter(Book.id.in_(data.ids))
        .update({Book.category: data.category}, synchronize_session=False)
    )
    db.commit()
    return {"updated": updated}


@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    return get_book_or_404(db, book_id)


@router.post("", response_model=BookOut, status_code=201)
def create_book(data: BookCreate, db: Session = Depends(get_db)):
    if data.isbn:
        if db.query(Book).filter(Book.isbn == data.isbn, Book.deleted_at.is_(None)).first():
            raise HTTPException(status_code=400, detail="该 ISBN 已存在")
        if db.query(Book).filter(Book.isbn == data.isbn, Book.deleted_at.isnot(None)).first():
            raise HTTPException(status_code=400, detail="该 ISBN 在回收站中，请先恢复或彻底删除")
    if data.category:
        ensure_category(db, data.category)
    book = Book(**data.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.put("/{book_id}", response_model=BookOut)
def update_book(book_id: int, data: BookUpdate, db: Session = Depends(get_db)):
    book = get_book_or_404(db, book_id)
    updates = data.model_dump(exclude_unset=True)

    new_isbn = updates.get("isbn")
    if new_isbn:
        duplicate = db.query(Book).filter(
            Book.isbn == new_isbn, Book.id != book_id, Book.deleted_at.is_(None)
        ).first()
        if duplicate:
            raise HTTPException(status_code=400, detail="该 ISBN 已存在")
        dup_deleted = db.query(Book).filter(
            Book.isbn == new_isbn, Book.id != book_id, Book.deleted_at.isnot(None)
        ).first()
        if dup_deleted:
            raise HTTPException(status_code=400, detail="该 ISBN 在回收站中，请先恢复或彻底删除")

    new_category = updates.get("category")
    if new_category:
        ensure_category(db, new_category)

    for field, value in updates.items():
        setattr(book, field, value)
    db.commit()
    db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=204)
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = get_book_or_404(db, book_id)
    _ensure_no_active_borrow(db, [book])
    _soft_delete(book)
    db.commit()
    return None


def _ensure_no_active_borrow(db: Session, books: list) -> None:
    """有在借记录的书不能进回收站，否则库存与借阅会对不上。"""
    blocked = []
    for b in books:
        active = (
            db.query(BorrowRecord)
            .filter(BorrowRecord.book_id == b.id, BorrowRecord.status == "在借")
            .count()
        )
        if active:
            blocked.append(f"《{b.title}》({active} 条在借)")
    if blocked:
        raise HTTPException(status_code=400, detail=f"请先归还：{ '、'.join(blocked) }")


def _soft_delete(book: Book) -> None:
    """软删除：标记时间；ISBN 挪出唯一索引冲突区，便于同 ISBN 重新入库。"""
    book.deleted_at = datetime.now()
    if book.isbn:
        book.isbn = f"{book.isbn}__{book.id}"


@router.post("/{book_id}/restore", response_model=BookOut)
def restore_book(book_id: int, db: Session = Depends(get_db), _: None = Depends(get_current_user)):
    book = db.query(Book).filter(Book.id == book_id, Book.deleted_at.isnot(None)).first()
    if not book:
        raise HTTPException(status_code=404, detail="回收站中不存在该图书")
    if book.isbn and "__" in book.isbn:
        candidate = book.isbn.rsplit("__", 1)[0]
        occupied = db.query(Book).filter(
            Book.isbn == candidate, Book.deleted_at.is_(None), Book.id != book.id
        ).first()
        if occupied:
            raise HTTPException(
                status_code=400,
                detail=f"ISBN {candidate} 已被在库图书《{occupied.title}》占用，无法恢复",
            )
        book.isbn = candidate
    book.deleted_at = None
    db.commit()
    db.refresh(book)
    return book


@router.delete("/{book_id}/purge", status_code=204)
def purge_book(book_id: int, db: Session = Depends(get_db), _: None = Depends(get_current_user)):
    book = db.query(Book).filter(Book.id == book_id, Book.deleted_at.isnot(None)).first()
    if not book:
        raise HTTPException(status_code=404, detail="回收站中不存在该图书")
    db.delete(book)
    db.commit()
    return None
