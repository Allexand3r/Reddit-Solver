async function getActiveTab() {
  let [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  return tab;
}
async function fetchContextFromPage() {
  const tab = await getActiveTab();
  const [{result}] = await chrome.scripting.executeScript({
    target: {tabId: tab.id},
    func: () => {
      const user = (document.querySelector('a[data-click-id="user"]')||{}).textContent || 'unknown';
      const comments = Array.from(document.querySelectorAll('div[data-test-id="comment"] p')).slice(0,3).map(p => (p.textContent||'').slice(0,300));
      return {user, comments};
    }
  });
  return result;
}
async function fetchSuggestions(ctx) {
  const cfg = await chrome.storage.sync.get('backend');
  const base = (cfg && cfg.backend) ? cfg.backend : 'http://127.0.0.1:8000';
  const user = {
    username: ctx.user.replace(/^u\//,'') || 'unknown',
    last_active_utc: Math.floor(Date.now()/1000),
    online_within_minutes: 5,
    comments: ctx.comments.map(c => ({permalink: '', body: c, created_utc: Math.floor(Date.now()/1000)}))
  };
  const res = await fetch(base + '/suggest', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({user, history: [], max_suggestions: 2})
  });
  return await res.json();
}
async function render() {
  const container = document.getElementById('suggestions');
  container.innerHTML = 'Loading…';
  try {
    const ctx = await fetchContextFromPage();
    const suggestions = await fetchSuggestions(ctx);
    container.innerHTML = '';
    suggestions.forEach(s => {
      const div = document.createElement('div');
      div.className = 'msg';
      div.textContent = s.text + ' (score ' + s.score + ')';
      container.appendChild(div);
    });
  } catch (e) {
    container.textContent = 'Error: ' + e;
  }
}
document.getElementById('refresh').addEventListener('click', render);
render();
