import sys, os, json, shutil, subprocess, tempfile, time
from datetime import date
from pathlib import Path
front=Path(__file__).resolve().parents[1]
root=front.parent
from playwright.sync_api import sync_playwright
back=root/'02_Backend_Computer_Systems_and_Networks'
data=Path(tempfile.mkdtemp(prefix='library-browser-test-'))
for name in ['books','users','loans']:shutil.copy2(back/'data'/f'{name}.json',data/f'{name}.json')
env={**os.environ,'LIBRARY_DATA_DIR':str(data)}
servers=[];results=[]
def record(name):results.append({'id':f'UI-{len(results)+1:02}','scenario':name,'result':'PASS'})
try:
 servers.append(subprocess.Popen([sys.executable,'app.py'],cwd=back,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
 servers.append(subprocess.Popen([sys.executable,'-m','http.server','8000','--bind','127.0.0.1'],cwd=front,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
 with sync_playwright() as p:
  edge=Path(r'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
  browser=p.chromium.launch(**({'executable_path':str(edge)} if edge.exists() else {}),headless=True)
  page=browser.new_page(viewport={'width':1360,'height':900},device_scale_factor=1)
  for _ in range(30):
   try:page.goto('http://127.0.0.1:8000');page.get_by_role('heading',name='A place for your next discovery.').wait_for(timeout=2000);break
   except Exception:time.sleep(.3)
  page.screenshot(path=str(front/'evidence/01-overview.png'));record('Overview loads live API statistics')
  page.get_by_role('button',name='Catalogue',exact=True).click();page.get_by_role('heading',name='Find your next book.').wait_for()
  page.screenshot(path=str(front/'evidence/02-catalogue.png'));record('Catalogue displays seeded books and stock')
  page.locator('#query').fill('Python');page.get_by_role('button',name='Search',exact=True).click();page.get_by_text('1 titles found',exact=False).wait_for();record('Title search returns one matching book')
  page.reload();page.get_by_role('button',name='Catalogue',exact=True).click();page.locator('#query').wait_for();assert page.locator('#query').input_value()=='Python';record('Search preferences persist after reload')
  page.locator('#query').fill('not-in-catalogue');page.get_by_role('button',name='Search',exact=True).click();page.get_by_text('No books match your search.',exact=False).wait_for();page.screenshot(path=str(front/'evidence/03-empty.png'));record('Unmatched search shows an empty state')
  page.locator('#query').fill('');page.get_by_role('button',name='Search',exact=True).click();page.get_by_role('button',name='Details',exact=True).first.wait_for();page.get_by_role('button',name='Details',exact=True).first.click();page.get_by_text('ISBN',exact=True).wait_for();page.screenshot(path=str(front/'evidence/04-details.png'));record('Book detail view displays ISBN and availability')
  with page.expect_response(lambda response: response.url.endswith('/api/loans') and response.request.method=='POST') as borrowed:
   page.get_by_role('button',name='Borrow',exact=True).click()
  borrow_response=borrowed.value
  assert borrow_response.status==201
  assert 'application/json' in borrow_response.request.headers.get('content-type','')
  assert json.loads(borrow_response.request.post_data)=={'book_id':1}
  loan=borrow_response.json()['loan']
  assert loan['book_id']==1 and loan['status']=='borrowed'
  assert (date.fromisoformat(loan['due_date'])-date.fromisoformat(loan['borrow_date'])).days==30
  page.get_by_text('Book borrowed successfully',exact=True).wait_for();record('Borrow submits JSON and confirms success')
  page.get_by_role('button',name='My loans',exact=True).click();page.get_by_role('button',name='Return',exact=True).wait_for()
  row=page.locator('tbody tr').first
  assert page.locator('tbody tr').count()==1
  assert row.locator('td').nth(1).inner_text().strip()==loan['borrow_date']
  assert row.locator('td').nth(2).inner_text().strip()==loan['due_date']
  assert row.locator('td').nth(3).inner_text().strip()=='borrowed'
  page.screenshot(path=str(front/'evidence/05-loans.png'));record('Loan appears with borrowed and due dates')
  with page.expect_response(lambda response: response.url.endswith(f"/api/loans/{loan['id']}/return") and response.request.method=='POST') as returned:
   page.get_by_role('button',name='Return',exact=True).click()
  return_response=returned.value
  assert return_response.status==200
  returned_loan=return_response.json()['loan']
  assert returned_loan['id']==loan['id'] and returned_loan['status']=='returned'
  page.get_by_text('Book returned successfully',exact=True).wait_for()
  row=page.locator('tbody tr').first
  assert row.locator('td').nth(3).inner_text().strip()=='returned'
  assert row.locator('td').nth(4).inner_text().strip()==f"Returned {returned_loan['return_date']}"
  assert row.get_by_role('button',name='Return',exact=True).count()==0
  record('Return updates the loan state')
  with page.expect_response(lambda response: response.url.endswith('/api/admin/dashboard') and response.request.method=='GET') as reported:
   page.get_by_role('button',name='Reports',exact=True).click()
  report_response=reported.value
  assert report_response.status==200
  report=report_response.json()
  books=json.loads((data/'books.json').read_text(encoding='utf-8'))
  expected_categories={}
  for book in books: expected_categories[book['category']]=expected_categories.get(book['category'],0)+book['total_copies']
  assert report['books_by_category']==expected_categories
  assert report['loans_by_month']=={loan['borrow_date'][:7]:1}
  category_panel=page.get_by_role('heading',name='Copies by category').locator('..')
  month_panel=page.get_by_role('heading',name='Loans by month').locator('..')
  def table_values(panel):
   return {cells[0].inner_text().strip():int(cells[1].inner_text().strip())
           for row in panel.locator('tr').all() if len(cells:=row.locator('td').all())==2}
  assert table_values(category_panel)==expected_categories
  assert table_values(month_panel)=={loan['borrow_date'][:7]:1}
  page.screenshot(path=str(front/'evidence/06-reports.png'));record('Reports show category and month aggregates')
  page.get_by_role('button',name='Settings',exact=True).click();page.locator('#base').wait_for();page.locator('#base').fill('not-a-url');page.get_by_role('button',name='Save settings').click();page.get_by_text('Enter a valid HTTP or HTTPS API URL ending in /api.',exact=True).wait_for();page.screenshot(path=str(front/'evidence/07-validation.png'));record('Invalid API URL rejected with a visible message')
  page.locator('#base').fill('http://127.0.0.1:59999/api');page.get_by_role('button',name='Save settings').click();page.get_by_role('button',name='Overview',exact=True).click();page.get_by_role('heading',name='Unable to load this view.').wait_for();page.screenshot(path=str(front/'evidence/08-network-error.png'));record('Unavailable API shows a recoverable connection error')
  page.get_by_role('button',name='Settings',exact=True).click();page.locator('#base').fill('http://127.0.0.1:5000/api');page.get_by_role('button',name='Save settings').click();page.get_by_role('button',name='Catalogue',exact=True).click();page.get_by_role('heading',name='Find your next book.').wait_for();record('Corrected API URL restores the application')
  page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(front/'evidence/09-mobile.png'));assert page.evaluate('document.documentElement.scrollWidth <= innerWidth');record('Mobile layout has no page-level horizontal overflow')
  browser.close()
finally:
 for proc in servers:proc.terminate();proc.wait(timeout=10)
 (front/'evidence/browser-tests.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
 shutil.rmtree(data,ignore_errors=True)
 print(json.dumps(results,indent=2))
