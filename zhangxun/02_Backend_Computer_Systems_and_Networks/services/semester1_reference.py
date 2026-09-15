from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Any

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
BOOKS_FILE = DATA_DIR / "books.json"
USERS_FILE = DATA_DIR / "users.json"
LOANS_FILE = DATA_DIR / "loans.json"


@dataclass
class Book:
    id: int
    title: str
    author: str
    isbn: str
    category: str
    total_copies: int
    available_copies: int
    created_at: str


@dataclass
class User:
    id: int
    name: str
    role: str  # "reader" or "admin"
    max_loans: int = 5


@dataclass
class Loan:
    id: int
    user_id: int
    book_id: int
    borrow_date: str
    due_date: str
    return_date: str | None
    status: str  # "borrowed" or "returned"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> List[Dict[str, Any]]:
    _ensure_data_dir()
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_json(path: Path, data: List[Dict[str, Any]]) -> None:
    _ensure_data_dir()
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _init_sample_data() -> None:
    # 若数据文件不存在，初始化一些示例数据，便于演示和测试
    if not BOOKS_FILE.exists():
        books = [
            asdict(
                Book(
                    id=1,
                    title="Python 程序设计入门",
                    author="张三",
                    isbn="978730000001",
                    category="计算机",
                    total_copies=5,
                    available_copies=5,
                    created_at=str(date.today()),
                )
            ),
            asdict(
                Book(
                    id=2,
                    title="数据结构与算法分析",
                    author="李四",
                    isbn="978730000002",
                    category="计算机",
                    total_copies=3,
                    available_copies=3,
                    created_at=str(date.today()),
                )
            ),
        ]
        _save_json(BOOKS_FILE, books)

    if not USERS_FILE.exists():
        users = [
            asdict(User(id=1, name="示例读者", role="reader", max_loans=5)),
            asdict(User(id=2, name="管理员", role="admin", max_loans=10)),
        ]
        _save_json(USERS_FILE, users)

    if not LOANS_FILE.exists():
        _save_json(LOANS_FILE, [])


def _load_books() -> List[Dict[str, Any]]:
    _init_sample_data()
    return _load_json(BOOKS_FILE)


def _load_users() -> List[Dict[str, Any]]:
    _init_sample_data()
    return _load_json(USERS_FILE)


def _load_loans() -> List[Dict[str, Any]]:
    _init_sample_data()
    return _load_json(LOANS_FILE)


def _save_books(books: List[Dict[str, Any]]) -> None:
    _save_json(BOOKS_FILE, books)


def _save_loans(loans: List[Dict[str, Any]]) -> None:
    _save_json(LOANS_FILE, loans)


def get_stats() -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """首页统计信息：总册数、在借册数、用户数、逾期数等。"""
    books = _load_books()
    loans = _load_loans()
    users = _load_users()

    total_books = sum(b["total_copies"] for b in books)
    borrowed_copies = sum(
        1 for l in loans if l["status"] == "borrowed"
    )  # 简化：一条记录代表一本书

    today = date.today()
    overdue_count = sum(
        1
        for l in loans
        if l["status"] == "borrowed" and date.fromisoformat(l["due_date"]) < today
    )

    stats = {
        "total_books": total_books,
        "borrowed_copies": borrowed_copies,
        "user_count": len(users),
        "overdue_count": overdue_count,
    }

    latest_books = sorted(books, key=lambda b: b["created_at"], reverse=True)[:5]
    latest_loans = sorted(loans, key=lambda l: l["borrow_date"], reverse=True)[:5]

    return stats, latest_books, latest_loans


def search_books(
    keyword: str, category: str, page: int, page_size: int
) -> Dict[str, Any]:
    books = _load_books()
    keyword_lower = keyword.strip().lower()
    category = category.strip()

    def match(book: Dict[str, Any]) -> bool:
        if category and book["category"] != category:
            return False
        if not keyword_lower:
            return True
        text = f'{book["title"]} {book["author"]} {book["isbn"]}'.lower()
        return keyword_lower in text

    filtered = [b for b in books if match(b)]

    total = len(filtered)
    page = max(page, 1)
    start = (page - 1) * page_size
    end = start + page_size
    page_books = filtered[start:end]
    total_pages = (total + page_size - 1) // page_size if total else 1

    categories = sorted({b["category"] for b in books})

    return {
        "books": page_books,
        "page": page,
        "total_pages": total_pages,
        "total": total,
        "keyword": keyword,
        "category": category,
        "categories": categories,
    }


def get_book(book_id: int) -> Dict[str, Any] | None:
    books = _load_books()
    for b in books:
        if b["id"] == book_id:
            return b
    return None


def borrow_book(user_id: int, book_id: int) -> Tuple[bool, str]:
    books = _load_books()
    loans = _load_loans()
    users = _load_users()

    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        return False, "用户不存在"

    book = next((b for b in books if b["id"] == book_id), None)
    if not book:
        return False, "图书不存在"

    if book["available_copies"] <= 0:
        return False, "库存不足，无法借阅"

    active_loans = [
        l for l in loans if l["user_id"] == user_id and l["status"] == "borrowed"
    ]
    if len(active_loans) >= user.get("max_loans", 5):
        return False, "已达到最大借阅册数"

    new_id = max((l["id"] for l in loans), default=0) + 1
    today = date.today()
    due = today + timedelta(days=30)
    new_loan = asdict(
        Loan(
            id=new_id,
            user_id=user_id,
            book_id=book_id,
            borrow_date=str(today),
            due_date=str(due),
            return_date=None,
            status="borrowed",
        )
    )
    loans.append(new_loan)

    # 更新库存
    book["available_copies"] -= 1
    _save_loans(loans)
    _save_books(books)
    return True, "借阅成功"


def return_book(loan_id: int) -> None:
    loans = _load_loans()
    books = _load_books()

    loan = next((l for l in loans if l["id"] == loan_id), None)
    if not loan or loan["status"] == "returned":
        return

    loan["status"] = "returned"
    loan["return_date"] = str(date.today())

    book = next((b for b in books if b["id"] == loan["book_id"]), None)
    if book:
        book["available_copies"] += 1

    _save_loans(loans)
    _save_books(books)


def get_user_loans(user_id: int) -> List[Dict[str, Any]]:
    loans = _load_loans()
    books = {b["id"]: b for b in _load_books()}
    today = date.today()

    result: List[Dict[str, Any]] = []
    for l in loans:
        if l["user_id"] != user_id:
            continue
        book = books.get(l["book_id"])
        if not book:
            continue
        due_date = date.fromisoformat(l["due_date"])
        is_overdue = l["status"] == "borrowed" and due_date < today
        result.append(
            {
                **l,
                "book_title": book["title"],
                "book_author": book["author"],
                "is_overdue": is_overdue,
            }
        )
    result.sort(key=lambda x: x["borrow_date"], reverse=True)
    return result


def get_admin_dashboard() -> Dict[str, Any]:
    books = _load_books()
    loans = _load_loans()

    # 按分类统计图书数量
    books_by_category: Dict[str, int] = {}
    for b in books:
        books_by_category[b["category"]] = books_by_category.get(b["category"], 0) + b[
            "total_copies"
        ]

    # 按月份统计借阅量（yyyy-mm）
    loans_by_month: Dict[str, int] = {}
    for l in loans:
        month = l["borrow_date"][:7]
        loans_by_month[month] = loans_by_month.get(month, 0) + 1

    return {
        "books": books,
        "loans": loans,
        "books_by_category": books_by_category,
        "loans_by_month": dict(sorted(loans_by_month.items())),
    }

