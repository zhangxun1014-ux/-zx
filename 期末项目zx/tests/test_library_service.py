import os
from datetime import date, timedelta
from pathlib import Path

from services import library_service as svc


def setup_module(module):
    """每个测试模块开始前，清空数据文件，确保测试可重复。"""
    data_dir = svc.DATA_DIR
    if data_dir.exists():
        for name in ["books.json", "users.json", "loans.json"]:
            path = data_dir / name
            if path.exists():
                os.remove(path)
    # 重新初始化示例数据
    svc._init_sample_data()  # type: ignore[attr-defined]


def test_search_books_by_keyword():
    result = svc.search_books("Python", "", page=1, page_size=10)
    assert result["total"] >= 1
    assert any("Python" in b["title"] for b in result["books"])


def test_borrow_and_return_book():
    # 初始状态下用户 1 没有借阅记录
    loans_before = svc.get_user_loans(1)
    assert loans_before == []

    # 借一本 id=1 的书
    ok, msg = svc.borrow_book(1, 1)
    assert ok, msg

    loans_after = svc.get_user_loans(1)
    assert len(loans_after) == 1
    loan = loans_after[0]
    assert loan["status"] == "borrowed"

    # 归还
    svc.return_book(loan["id"])
    loans_after_return = svc.get_user_loans(1)
    assert loans_after_return[0]["status"] == "returned"
    assert loans_after_return[0]["return_date"] is not None


def test_overdue_detection():
    # 人工写入一条逾期借阅记录
    books = svc._load_books()  # type: ignore[attr-defined]
    loans = svc._load_loans()  # type: ignore[attr-defined]

    new_id = max((l["id"] for l in loans), default=0) + 1
    overdue_loan = {
        "id": new_id,
        "user_id": 1,
        "book_id": books[0]["id"],
        "borrow_date": str(date.today() - timedelta(days=40)),
        "due_date": str(date.today() - timedelta(days=10)),
        "return_date": None,
        "status": "borrowed",
    }
    loans.append(overdue_loan)
    svc._save_loans(loans)  # type: ignore[attr-defined]

    user_loans = svc.get_user_loans(1)
    assert any(l["is_overdue"] for l in user_loans)


def test_admin_dashboard_stats():
    dashboard = svc.get_admin_dashboard()
    assert "books_by_category" in dashboard
    assert "loans_by_month" in dashboard

