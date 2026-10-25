// Feed panel: reads the research feed API served by the same origin. Token lives only in this browser.
(function () {
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const empty = t => `<div class="empty">${esc(t)}</div>`;
  const safeUrl = u => { try { const p = new URL(u, location.href); return (p.protocol === 'http:' || p.protocol === 'https:') ? p.href : '#'; } catch (e) { return '#'; } };
  const KEY = 'feed_token';
  const STALE_HOURS = 24;
  const $ = id => document.getElementById(id);
  let token = '';
  try { token = localStorage.getItem(KEY) || ''; } catch (e) { token = ''; }

  function api(path) {
    return fetch(path, { headers: token ? { Authorization: 'Bearer ' + token } : {} }).then(r => {
      if (r.status === 401) throw new Error('token rejected');
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function latestMetrics(raw) {
    let m = raw;
    if (typeof m === 'string') { try { m = JSON.parse(m || '{}'); } catch (e) { m = {}; } }
    if (!m || typeof m !== 'object') return {};
    const keys = Object.keys(m);
    if (keys.length && keys.every(k => m[k] && typeof m[k] === 'object')) return m[keys.sort().pop()];
    return m;
  }

  function renderStats(s) {
    const lanes = Object.entries(s.lanes || {}).filter(([, c]) => Object.values(c).some(v => v));
    const laneRows = lanes.map(([lane, c]) => `<tr><td>${esc(lane)}</td><td>${c.collected}</td><td>${c.offered}</td><td>${c.shown}</td><td>${c.picked}</td><td>${c.posted}</td></tr>`).join('');
    const now = Date.now();
    const last = Object.entries(s.last_collected || {}).map(([p, when]) => {
      const ageH = (now - Date.parse(when)) / 36e5;
      const stale = !(ageH < STALE_HOURS);
      return `<span class="pill ${stale ? '' : 'active'}" ${stale ? 'style="color:var(--alert);border-color:var(--alert)"' : ''}>${esc(p)} · ${isFinite(ageH) ? Math.round(ageH) + 'h ago' : 'never'}</span>`;
    }).join(' ');
    const sources = (s.sources || []).slice(0, 8).map(x => `<div class="row"><strong>${esc(x.source)}</strong><span class="pill">${x.picked}/${x.collected} picked · ${Math.round(x.pick_rate * 100)}%</span></div>`).join('');
    $('feed-stats').innerHTML = (lanes.length ? `<table class="table"><tr><th>lane</th><th>collected</th><th>offered</th><th>shown</th><th>picked</th><th>posted</th></tr>${laneRows}</table>` : empty('No items collected in the last 7 days.'))
      + `<div class="muted" style="margin-top:10px">LAST COLLECTED ${last || '—'}</div>` + (sources ? `<div style="margin-top:12px">${sources}</div>` : '');
  }

  function renderItems(items) {
    $('feed-items').innerHTML = items.length ? items.map(i => {
      const m = latestMetrics(i.metrics);
      const metrics = ['installs', 'stars'].filter(k => m[k] != null).map(k => `${k} ${m[k]}`).join(' · ');
      return `<div class="row"><strong><a href="${esc(safeUrl(i.url))}" target="_blank" rel="noopener noreferrer">${esc(i.title)} →</a></strong>`
        + `<span class="pill ${i.status === 'picked' || i.status === 'posted' ? 'active' : ''}">${esc(i.lane)} · ${esc(i.status)}</span> <span class="pill">score ${i.score}</span> <span class="pill">${esc(i.source)}${metrics ? ' · ' + esc(metrics) : ''}</span>`
        + (i.insight ? `<div class="muted">${esc(i.insight)}</div>` : '') + (i.pick_note ? `<div class="muted">↳ ${esc(i.pick_note)}</div>` : '') + `</div>`;
    }).join('') : empty('Nothing offered yet.');
  }

  function load() {
    if (!token) { $('feed-stats').innerHTML = empty('Enter the feed token to load stats.'); $('feed-items').innerHTML = ''; return; }
    Promise.all([api('/api/stats?days=7'), api('/api/items?status=offered,shown,picked&limit=30')])
      .then(([stats, items]) => { renderStats(stats); renderItems(items.items || []); })
      .catch(e => { $('feed-stats').innerHTML = empty('Feed: ' + e.message); $('feed-items').innerHTML = ''; });
  }

  const input = $('feed-token');
  if (input) {
    input.value = token;
    input.addEventListener('change', () => { token = input.value.trim(); try { localStorage.setItem(KEY, token); } catch (e) { } load(); });
  }
  load();

  // Legacy prebuilt sections: hide them when data.json is not deployed with the service.
  window.feedHideLegacyOn404 = r => { if (r.status === 404) { document.querySelectorAll('[data-legacy]').forEach(el => el.style.display = 'none'); return null; } return r; };
})();
