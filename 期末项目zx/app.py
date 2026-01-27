from flask import Flask, render_template, request, redirect, url_for

from services.library_service import (
    get_stats,
    search_books,
    get_book,
    borrow_book,
    get_user_loans,
    return_book,
    get_admin_dashboard,
)


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        stats, latest_books, latest_loans = get_stats()
        return render_template(
            "index.html",
            stats=stats,
            latest_books=latest_books,
            latest_loans=latest_loans,
        )

    @app.route("/books")
    def books():
        keyword = request.args.get("q", "")
        category = request.args.get("category", "")
        page = int(request.args.get("page", 1) or 1)
        page_size = 10
        result = search_books(keyword, category, page, page_size)
        return render_template("books.html", **result)

    @app.route("/books/<int:book_id>", methods=["GET", "POST"])
    def book_detail(book_id: int):
        # Simplified: assume current user id = 1 instead of full auth system
        user_id = 1

        if request.method == "POST":
            success, message = borrow_book(user_id, book_id)
            if not success:
                book = get_book(book_id)
                return render_template(
                    "book_detail.html",
                    book=book,
                    error=message,
                )
            return redirect(url_for("my_loans"))

        book = get_book(book_id)
        return render_template("book_detail.html", book=book)

    @app.route("/my/loans", methods=["GET", "POST"])
    def my_loans():
        user_id = 1
        if request.method == "POST":
            loan_id = int(request.form["loan_id"])
            return_book(loan_id)
            return redirect(url_for("my_loans"))

        loans = get_user_loans(user_id)
        return render_template("my_loans.html", loans=loans)

    @app.route("/admin")
    def admin():
        dashboard = get_admin_dashboard()
        return render_template("admin.html", dashboard=dashboard)

    return app


if __name__ == "__main__":
    create_app().run(debug=True)

