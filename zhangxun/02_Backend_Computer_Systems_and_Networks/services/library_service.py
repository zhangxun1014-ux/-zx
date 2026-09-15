"""Second-semester evolution of the original JSON library service.

The original search, stock, 30-day due date and aggregation rules are retained.
All mutable state now lives in one atomically replaced UTF-8 JSON document.
One process only: the RLock protects threads, not multiple server processes.
"""
import json
import os
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from threading import RLock

class LibraryError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status

class LibraryService:
    def __init__(self, data_dir):
        self.directory = Path(data_dir)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / 'library.json'
        self.lock = RLock()
        if not self.path.exists():
            state = {}
            for entity in ('books', 'users', 'loans'):
                state[entity] = json.loads((self.directory / (entity + '.json')).read_text(encoding='utf-8'))
            self._save(state)
        self._load()

    def _load(self):
        # Corrupt files must fail visibly; never silently reset persisted records.
        state = json.loads(self.path.read_text(encoding='utf-8'))
        if not all(isinstance(state.get(k), list) for k in ('books', 'users', 'loans')):
            raise ValueError('Invalid library data schema')
        return state

    def _save(self, state):
        temp = self.path.with_suffix('.tmp')
        with temp.open('w', encoding='utf-8') as stream:
            json.dump(state, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, self.path)

    def snapshot(self):
        with self.lock:
            return deepcopy(self._load())

    @staticmethod
    def find(records, identifier, label):
        item = next((row for row in records if row['id'] == identifier), None)
        if item is None:
            raise LibraryError(label + ' not found', 404)
        return item

    def search_books(self, keyword='', category='', page=1, page_size=10):
        books = self.snapshot()['books']
        query = keyword.strip().casefold()
        category = category.strip()
        selected = [b for b in books if (not category or b['category'] == category)
                    and (not query or query in f"{b['title']} {b['author']} {b['isbn']}".casefold())]
        start = (page - 1) * page_size
        return {'books': selected[start:start+page_size], 'page': page, 'page_size': page_size,
                'total': len(selected), 'total_pages': max(1, (len(selected)+page_size-1)//page_size),
                'categories': sorted({b['category'] for b in books})}

    def get_book(self, book_id):
        return self.find(self.snapshot()['books'], book_id, 'Book')

    def get_loans(self, user_id=1):
        state = self.snapshot()
        self.find(state['users'], user_id, 'Reader')
        books = {b['id']: b for b in state['books']}
        return [{**loan, 'book_title': books[loan['book_id']]['title'],
                 'book_author': books[loan['book_id']]['author'],
                 'is_overdue': loan['status'] == 'borrowed' and loan['due_date'] < str(date.today())}
                for loan in reversed(state['loans']) if loan['user_id'] == user_id]

    def borrow(self, book_id, user_id=1):
        with self.lock:
            state = self._load()
            reader = self.find(state['users'], user_id, 'Reader')
            book = self.find(state['books'], book_id, 'Book')
            active = [l for l in state['loans'] if l['user_id'] == user_id and l['status'] == 'borrowed']
            if book['available_copies'] <= 0:
                raise LibraryError('No copies available', 409)
            if len(active) >= reader.get('max_loans', 5):
                raise LibraryError('Reader loan limit reached', 409)
            loan = {'id': max((l['id'] for l in state['loans']), default=0)+1,
                    'user_id': user_id, 'book_id': book_id, 'borrow_date': str(date.today()),
                    'due_date': str(date.today()+timedelta(days=30)), 'return_date': None, 'status': 'borrowed'}
            state['loans'].append(loan)
            book['available_copies'] -= 1
            self._save(state)
            return loan

    def return_loan(self, loan_id, user_id=1):
        with self.lock:
            state = self._load()
            loan = self.find(state['loans'], loan_id, 'Loan')
            if loan['user_id'] != user_id:
                raise LibraryError('Loan belongs to another reader', 403)
            if loan['status'] == 'returned':
                return loan
            book = self.find(state['books'], loan['book_id'], 'Book')
            loan.update(status='returned', return_date=str(date.today()))
            book['available_copies'] += 1
            self._save(state)
            return loan

    def stats(self):
        state = self.snapshot()
        active = [l for l in state['loans'] if l['status'] == 'borrowed']
        return {'total_books': sum(b['total_copies'] for b in state['books']),
                'borrowed_copies': len(active), 'user_count': len(state['users']),
                'overdue_count': sum(l['due_date'] < str(date.today()) for l in active)}

    def dashboard(self):
        state = self.snapshot()
        categories, months = {}, {}
        for book in state['books']:
            key = book['category']
            categories[key] = categories.get(key, 0) + book['total_copies']
        for loan in state['loans']:
            key = loan['borrow_date'][:7]
            months[key] = months.get(key, 0) + 1
        return {'books_by_category': categories, 'loans_by_month': dict(sorted(months.items()))}
