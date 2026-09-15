export function validateBase(value) {
  try { const url=new URL(value); return ['http:','https:'].includes(url.protocol) && !url.username && !url.password && !url.search && !url.hash && /\/api\/?$/.test(url.pathname); }
  catch { return false; }
}
export function readSaved() {
  try { return JSON.parse(localStorage.getItem('library.preferences') || '{}') || {}; } catch { return {}; }
}
export function savePreferences(value) {
  try { localStorage.setItem('library.preferences',JSON.stringify(value)); return true; } catch { return false; }
}
export async function request(base,path,options={}) {
  const controller=new AbortController(); const timer=setTimeout(()=>controller.abort(),8000);
  try {
    const response=await fetch(base+path,{...options,signal:controller.signal,headers:{...(options.body?{'Content-Type':'application/json'}:{}),...options.headers}});
    const data=await response.json();
    if(!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
    return data;
  } catch(error) {
    if(error.name==='AbortError') throw new Error('The server did not respond within 8 seconds. Try again.');
    if(error instanceof TypeError) throw new Error('Cannot connect to the API. Start the backend and check Settings.');
    throw error;
  } finally { clearTimeout(timer); }
}
