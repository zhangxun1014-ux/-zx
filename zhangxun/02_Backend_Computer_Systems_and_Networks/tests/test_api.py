import json
import shutil
from datetime import date, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from app import create_app

@pytest.fixture
def app(tmp_path):
    for name in ('books', 'users', 'loans'):
        shutil.copy(Path(__file__).parents[1]/'data'/f'{name}.json', tmp_path/f'{name}.json')
    app = create_app(tmp_path)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.mark.parametrize('path', ['/api/health','/api/books','/api/books/1','/api/loans','/api/stats','/api/admin/dashboard','/api/openapi.json'])
def test_read_endpoints(client, path):
    assert client.get(path).status_code == 200

@pytest.mark.parametrize('value', [None, True, False, '1', 0, -1, 1.5, [], {}, 999])
def test_invalid_book_id(client, value):
    response = client.post('/api/loans', json={'book_id':value})
    assert response.status_code == (404 if value == 999 else 400)
    assert 'error' in response.json
    assert client.get('/api/stats').json['stats']['borrowed_copies'] == 0

@pytest.mark.parametrize('body', [[], {}, {'book_id':1,'user_id':2}, 'text', None])
def test_bad_body(client, body):
    assert client.post('/api/loans', data=json.dumps(body), content_type='application/json').status_code == 400

@pytest.mark.parametrize('query', ['page=0','page=-1','page=x','page_size=51','page_size=0','page=1.5','q='+'x'*101,'category='+'x'*81])
def test_bad_query(client, query):
    assert client.get('/api/books?'+query).status_code == 400

def test_search_and_paging(client):
    assert client.get('/api/books?q=Python').json['total'] == 1
    assert client.get('/api/books?q=not-in-catalogue').json['books'] == []
    assert client.get('/api/books?category=计算机&page_size=1').json['total_pages'] == 2
    assert client.get('/api/books?page=999').json['books'] == []

def test_category_filter_trims_whitespace_like_semester1(client):
    plain = client.get('/api/books', query_string={'category': '计算机'}).json
    padded = client.get('/api/books', query_string={'category': ' 计算机 '}).json
    assert padded['books'] == plain['books']
    assert padded['total'] == plain['total'] == 2

def test_borrow_return_lifecycle(client, app):
    before = client.get('/api/books/1').json['available_copies']
    response = client.post('/api/loans', json={'book_id':1})
    assert response.status_code == 201
    loan = response.json['loan']
    assert loan['due_date'] == str(date.today()+timedelta(days=30))
    assert client.get(response.headers['Location']).json['status'] == 'borrowed'
    assert client.get('/api/books/1').json['available_copies'] == before-1
    assert client.get('/api/loans').json['loans'][0]['book_title']
    assert client.post(f"/api/loans/{loan['id']}/return").json['loan']['status'] == 'returned'
    assert client.post(f"/api/loans/{loan['id']}/return").status_code == 200
    assert client.get('/api/books/1').json['available_copies'] == before
    assert create_app(app.extensions['library'].directory).test_client().get('/api/loans').json['loans'][0]['status'] == 'returned'

def test_stock_conflict(client):
    for _ in range(3):
        assert client.post('/api/loans', json={'book_id':2}).status_code == 201
    assert client.post('/api/loans', json={'book_id':2}).status_code == 409

def test_limit_conflict(client):
    for _ in range(5):
        assert client.post('/api/loans', json={'book_id':1}).status_code == 201
    assert client.post('/api/loans', json={'book_id':2}).status_code == 409

@pytest.mark.parametrize('path,method,code', [('/api/books/999','get',404),('/api/loans/999','get',404),('/api/loans/999/return','post',404),('/api/no-route','get',404),('/api/books','delete',405)])
def test_http_errors(client,path,method,code):
    response=getattr(client,method)(path)
    assert response.status_code == code and 'error' in response.json

def test_json_and_content_type(client):
    assert client.post('/api/loans', data='{bad', content_type='application/json').status_code == 400
    assert client.post('/api/loans', data='book_id=1').status_code == 415

def test_cors(client):
    assert client.get('/api/books', headers={'Origin':'http://127.0.0.1:8000'}).headers['Access-Control-Allow-Origin'] == 'http://127.0.0.1:8000'
    assert 'Access-Control-Allow-Origin' not in client.get('/api/books',headers={'Origin':'https://example.org'}).headers

def test_concurrent_borrow(app):
    def borrow(_):
        with app.test_client() as c:
            return c.post('/api/loans',json={'book_id':2}).status_code
    with ThreadPoolExecutor(max_workers=6) as pool:
        codes=list(pool.map(borrow,range(6)))
    assert codes.count(201)==3 and codes.count(409)==3
    state=app.extensions['library'].snapshot()
    assert len(state['loans'])==3 and state['books'][1]['available_copies']==0

def test_overdue_and_aggregate(client,app):
    client.post('/api/loans',json={'book_id':1})
    service=app.extensions['library']; state=service.snapshot()
    state['loans'][0]['due_date']=str(date.today()-timedelta(days=1));service._save(state)
    assert client.get('/api/stats').json['stats']['overdue_count']==1
    assert client.get('/api/loans').json['loans'][0]['is_overdue'] is True
    assert sum(client.get('/api/admin/dashboard').json['loans_by_month'].values())==1
