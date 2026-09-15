import {request,readSaved,savePreferences,validateBase} from './api.js';
const saved=readSaved();
const state={base:validateBase(saved.base)?saved.base.replace(/\/$/,''):'http://127.0.0.1:5000/api',query:typeof saved.query==='string'?saved.query:'',category:typeof saved.category==='string'?saved.category:'',page:1,view:'home',generation:0};
const content=document.querySelector('#content');const message=document.querySelector('#message');
const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const api=(path,options)=>request(state.base,path,options);
function notify(text,error=false){message.textContent=text;message.className=text?(error?'error':'success'):'';}
function persist(){const saved=savePreferences({base:state.base,query:state.query,category:state.category});if(!saved)notify('Browser storage is unavailable; preferences apply only in this session.',true);return saved;}
const button=(text,action,id,disabled=false)=>`<button data-action="${action}" data-id="${id}" ${disabled?'disabled':''}>${text}</button>`;
async function show(view=state.view){
 state.view=view;const generation=++state.generation;content.setAttribute('aria-busy','true');
 document.querySelectorAll('nav button').forEach(b=>b.setAttribute('aria-current',b.dataset.view===view?'page':'false'));
 content.innerHTML='<p>Loading…</p>';
 try{
  let html='';
  if(view==='home'){
   const {stats}=await api('/stats');
   html='<h1>A place for your next discovery.</h1><p class="muted">Browse the catalogue, borrow a book and keep track of your reading.</p><div class="cards">'+Object.entries({'Total copies':stats.total_books,'On loan':stats.borrowed_copies,'Readers':stats.user_count,'Overdue':stats.overdue_count}).map(([k,v])=>`<div class="card">${k}<strong>${v}</strong></div>`).join('')+'</div><div class="panel"><h2>Your library, one place.</h2><p>Search by title, author or ISBN. Loans are due in 30 days. This demonstration uses reader 1.</p><button data-action="catalogue">Explore catalogue</button></div>';
  } else if(view==='books'){
   const params=new URLSearchParams({q:state.query,category:state.category,page:String(state.page),page_size:'10'});const data=await api('/books?'+params);
   html=`<h1>Find your next book.</h1><p class="muted">${data.total} titles found · Search the library catalogue</p><form id="search" class="toolbar" novalidate><label>Title, author or ISBN<input id="query" name="q" maxlength="100" value="${escape(state.query)}" placeholder="Search the catalogue"></label><label>Category<select id="category"><option value="">All categories</option>${data.categories.map(c=>`<option ${c===state.category?'selected':''}>${escape(c)}</option>`).join('')}</select></label><button>Search</button></form>`;
   html+=data.books.length?`<div class="table-wrap"><table><thead><tr><th>Title / author</th><th>Category</th><th>Available</th><th>Actions</th></tr></thead><tbody>${data.books.map(b=>`<tr><td><strong>${escape(b.title)}</strong><br><span class="muted">${escape(b.author)}</span></td><td>${escape(b.category)}</td><td>${b.available_copies} / ${b.total_copies}</td><td>${button('Details','detail',b.id)} ${button('Borrow','borrow',b.id,b.available_copies===0)}</td></tr>`).join('')}</tbody></table></div>`:'<div class="panel empty">No books match your search. Try another title or category.</div>';
   html+=`<div class="pager">${button('Previous','previous','',state.page<=1)}<span>Page ${state.page} of ${data.total_pages}</span>${button('Next','next','',state.page>=data.total_pages)}</div>`;
  } else if(view==='loans'){
   const {loans}=await api('/loans');
   html='<h1>Your reading record.</h1><p class="muted">Current loans and returned books · Reader 1</p>';
   html+=loans.length?`<div class="table-wrap"><table><thead><tr><th>Book</th><th>Borrowed</th><th>Due date</th><th>Status</th><th>Action</th></tr></thead><tbody>${loans.map(l=>`<tr><td>${escape(l.book_title)}</td><td>${escape(l.borrow_date)}</td><td>${escape(l.due_date)}</td><td><span class="badge">${l.is_overdue?'Overdue':escape(l.status)}</span></td><td>${l.status==='borrowed'?button('Return','return',l.id):'Returned '+escape(l.return_date||'')}</td></tr>`).join('')}</tbody></table></div>`:'<div class="panel empty">No loans yet. Browse the catalogue to borrow your first book.</div>';
  } else if(view==='reports'){
   const data=await api('/admin/dashboard');html='<h1>Library at a glance.</h1><p class="muted">Aggregate collection and circulation statistics</p>';
   for(const [title,rows] of [['Copies by category',data.books_by_category],['Loans by month',data.loans_by_month]])html+=`<div class="panel"><h2>${title}</h2>${Object.keys(rows).length?'<table>'+Object.entries(rows).map(([k,v])=>`<tr><td>${escape(k)}</td><td>${v}</td></tr>`).join('')+'</table>':'<p>No circulation records.</p>'}</div>`;
  } else if(view==='settings'){
   html=`<h1>Connection settings.</h1><p class="muted">Your API address and last search are saved in this browser.</p><form id="settings" class="panel" novalidate><label>API base URL<input id="base" type="url" required value="${escape(state.base)}"></label><p>Use an HTTP or HTTPS URL ending in /api. Local backend: http://127.0.0.1:5000/api</p><button>Save settings</button></form>`;
  }
  if(generation===state.generation)content.innerHTML=html;
 }catch(error){if(generation===state.generation){notify(error.message,true);content.innerHTML='<h1>Unable to load this view.</h1><button data-action="retry">Retry</button>';}}
 finally{if(generation===state.generation)content.setAttribute('aria-busy','false');}
}
document.querySelector('nav').addEventListener('click',e=>{if(e.target.dataset.view){notify('');show(e.target.dataset.view);}});
content.addEventListener('submit',e=>{
 e.preventDefault();notify('');
 if(e.target.id==='search'){
  const query=document.querySelector('#query').value.trim();if(query.length>100){notify('Search must be 100 characters or fewer.',true);return;}
  state.query=query;state.category=document.querySelector('#category').value;state.page=1;persist();show('books');
 }else if(e.target.id==='settings'){
  const base=document.querySelector('#base').value.trim();if(!validateBase(base)){notify('Enter a valid HTTP or HTTPS API URL ending in /api.',true);return;}
  state.base=base.replace(/\/$/,'');if(persist())notify('Settings saved.');
 }
});
content.addEventListener('click',async e=>{
 const target=e.target.closest('button[data-action]');if(!target)return;const action=target.dataset.action;const id=Number(target.dataset.id);
 if(action==='catalogue')return show('books');if(action==='retry')return show();
 if(action==='next'||action==='previous'){state.page+=action==='next'?1:-1;return show('books');}
 if(!Number.isSafeInteger(id)||id<1)return notify('Select a valid book or loan.',true);
 target.disabled=true;notify('');const generation=state.generation;
 try{
  if(action==='detail'){
   const b=await api('/books/'+id);if(generation!==state.generation)return;
   content.innerHTML=`<h1>${escape(b.title)}</h1><div class="panel"><dl class="detail"><dt>Author</dt><dd>${escape(b.author)}</dd><dt>ISBN</dt><dd>${escape(b.isbn)}</dd><dt>Category</dt><dd>${escape(b.category)}</dd><dt>Availability</dt><dd>${b.available_copies} of ${b.total_copies}</dd></dl>${button('Borrow','borrow',b.id,b.available_copies===0)} <button data-action="catalogue" class="secondary">Back to catalogue</button></div>`;
  }else{
   const result=await api(action==='borrow'?'/loans':`/loans/${id}/return`,{method:'POST',...(action==='borrow'?{body:JSON.stringify({book_id:id})}:{})});
   if(generation===state.generation){await show(action==='borrow'?'books':'loans');notify(result.message);}
  }
 }catch(error){if(generation===state.generation)notify(error.message,true);}finally{target.disabled=false;}
});
show();
