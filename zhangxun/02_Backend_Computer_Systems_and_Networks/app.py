"""HTTP JSON API for the second-semester library backend course project."""
import os
from pathlib import Path
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from services.library_service import LibraryService, LibraryError

def positive_integer(value, name, maximum=None):
    if type(value) is not int or value < 1 or (maximum and value > maximum):
        raise LibraryError(name + ' must be a positive integer' + (f' <= {maximum}' if maximum else ''))
    return value

def query_integer(name, default, maximum):
    raw = request.args.get(name, str(default))
    if not raw.isascii() or not raw.isdecimal():
        raise LibraryError(name + ' must be a positive integer')
    return positive_integer(int(raw), name, maximum)

def create_app(data_dir=None):
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024
    service = LibraryService(data_dir or os.environ.get('LIBRARY_DATA_DIR') or Path(__file__).parent/'data')
    app.extensions['library'] = service
    CORS(app, resources={r'/api/*': {'origins': ['http://127.0.0.1:8000', 'http://localhost:8000']}})

    @app.errorhandler(LibraryError)
    def business_error(error):
        return jsonify(error=str(error)), error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.get('/api/health')
    def health():
        return jsonify(status='ok', mode='single-process course demonstration', reader_id=1)

    @app.get('/api/books')
    def books():
        keyword = request.args.get('q', '')
        category = request.args.get('category', '')
        if len(keyword) > 100 or len(category) > 80:
            raise LibraryError('Search text is too long')
        return jsonify(service.search_books(keyword, category, query_integer('page', 1, 100000),
                                            query_integer('page_size', 10, 50)))

    @app.get('/api/books/<int:book_id>')
    def book(book_id):
        return jsonify(service.get_book(book_id))

    @app.route('/api/loans', methods=['GET', 'POST'])
    def loans():
        if request.method == 'GET':
            return jsonify(loans=service.get_loans())
        data = request.get_json()
        if not isinstance(data, dict) or set(data) != {'book_id'}:
            raise LibraryError('Body must be an object containing only book_id')
        loan = service.borrow(positive_integer(data['book_id'], 'book_id'))
        response = jsonify(message='Book borrowed successfully', loan=loan)
        response.status_code = 201
        response.headers['Location'] = '/api/loans/' + str(loan['id'])
        return response

    @app.get('/api/loans/<int:loan_id>')
    def loan_detail(loan_id):
        return jsonify(service.find(service.get_loans(), loan_id, 'Loan'))

    @app.post('/api/loans/<int:loan_id>/return')
    def return_loan(loan_id):
        return jsonify(message='Book returned successfully', loan=service.return_loan(loan_id))

    @app.get('/api/stats')
    def stats():
        return jsonify(stats=service.stats())

    @app.get('/api/admin/dashboard')
    def dashboard():
        # Aggregate demonstration view only; no authentication is claimed.
        return jsonify(service.dashboard())

    @app.get('/api/openapi.json')
    def openapi():
        return send_file(Path(__file__).parent/'openapi.json', mimetype='application/json')

    return app

if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=5000, debug=False, threaded=True)
