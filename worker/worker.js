// 식단 앱 칼로리 사전 검색용 Cloudflare Worker (server.py의 /api/ds/* 와 같은 일)
//  GET /api/ds/ping
//  GET /api/ds/search?q=김밥&page=1  → {items:[{idx,n,b,kcal}], more}
//  GET /api/ds/food?idx=123&name=김밥 → {label, amount, unit, kcal}
// 사용자가 앱에서 검색할 때만 한 번씩 물어보고, 결과는 하루 동안 캐시한다.

const BASE = 'https://www.dietshin.com/calorie/';
const HEADERS = {
  'User-Agent': 'Mozilla/5.0 (personal diet app; on-demand lookup)',
  'Accept': 'text/html,application/xhtml+xml',
  'Accept-Language': 'ko-KR,ko;q=0.9',
  'Cache-Control': 'no-cache', 'Pragma': 'no-cache',
};
// 이 주소에서 연 앱만 쓸 수 있게
const ALLOW = [/^https:\/\/charaing\.github\.io$/, /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/];

const ENT = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', '#39': "'" };
const unescape = s => s.replace(/&(#x[\da-f]+|#\d+|\w+);/gi, (m, e) =>
  e[0] === '#' ? String.fromCodePoint(e[1] === 'x' || e[1] === 'X' ? parseInt(e.slice(2), 16) : +e.slice(1)) : ENT[e.toLowerCase()] ?? m);
const strip = s => unescape(s.replace(/<[^>]+>/g, '')).trim();
const escHtml = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
const num = s => parseFloat(s.replace(/,/g, ''));

async function get(url, check) {
  // check(text) 가 참일 때만 인정 (다른 검색어 페이지가 섞여 오는 경우 방지), 한 번 더 시도
  for (let i = 0; i < 2; i++) {
    const r = await fetch(url, { headers: HEADERS, cf: { cacheTtl: 0 } });
    const t = await r.text();
    if (r.ok && check(t)) return t;
    if (i === 0) await new Promise(s => setTimeout(s, 1000));
  }
  throw new Error('칼로리 사전 응답이 검색어와 맞지 않아요');
}

export async function search(q, page) {
  const url = BASE + 'calorie_search.asp?keyword=' + encodeURIComponent(q) + (page > 1 ? `&gotopage=${page}` : '');
  const t = await get(url, t => !t.includes('calorie-foodview') || t.includes(`<font color='red'>${escHtml(q)}</font>`) || t.includes(`<font color='red'>${q}</font>`));
  const ROW = /calorie-foodview\.asp\?cal_idx=(\d+)&cal_type=F">([\s\S]*?)<\/a><\/td>\s*<td>\s*([\d.,]+)\s*kcal/g;
  const items = [];
  for (const [, idx, raw, kcal] of t.matchAll(ROW)) {
    let n = strip(raw), b = '';
    const m = n.match(/^\[([^\]]+)\]\s*(.*)$/);
    if (m) [b, n] = [m[1], m[2]];
    items.push({ idx, n, b, kcal: num(kcal) });
  }
  return { items, more: t.includes(`gotopage=${page + 1}"`) };
}

export async function food(idx, name = '') {
  const want = name.replace(/\s/g, '');
  const t = await get(BASE + `calorie-foodview.asp?cal_idx=${parseInt(idx, 10)}&cal_type=F`,
    t => !want || strip(t).replace(/\s+/g, '').includes(want));
  const flat = strip(t).replace(/\s+/g, ' ');
  let m = flat.match(/(\d[\d.]*\s*\S{0,4}?)\s*\(\s*([\d.,]+)\s*(g|ml|mL|kg|L)\s*\)\s*칼로리\s*([\d.,]+)\s*kcal/);
  if (m) {
    let amt = num(m[2]), unit = m[3].toLowerCase();
    if (unit === 'kg') [amt, unit] = [amt * 1000, 'g'];
    if (unit === 'l') [amt, unit] = [amt * 1000, 'ml'];
    return { label: m[1].trim(), amount: amt, unit, kcal: num(m[4]) };
  }
  m = flat.match(/(\S{1,12})\s*칼로리\s*([\d.,]+)\s*kcal/);
  return { label: m ? m[1] : '1인분', amount: null, unit: null, kcal: m ? num(m[2]) : null };
}

function cors(req) {
  const o = req.headers.get('Origin') || '';
  return ALLOW.some(r => r.test(o)) ? { 'Access-Control-Allow-Origin': o, 'Vary': 'Origin' } : {};
}

export default {
  async fetch(req, env, ctx) {
    const u = new URL(req.url), h = cors(req);
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: { ...h, 'Access-Control-Allow-Methods': 'GET' } });
    if (req.method !== 'GET' || !u.pathname.startsWith('/api/ds/')) return new Response('not found', { status: 404 });

    const cache = globalThis.caches?.default, key = new Request(u.toString());
    if (cache && u.pathname !== '/api/ds/ping') {
      const hit = await cache.match(key);
      if (hit) { const r = new Response(hit.body, hit); for (const [k, v] of Object.entries(h)) r.headers.set(k, v); return r; }
    }
    let data, status = 200;
    try {
      const p = u.searchParams;
      if (u.pathname === '/api/ds/ping') data = { ok: true };
      else if (u.pathname === '/api/ds/search') {
        const q = (p.get('q') || '').trim().slice(0, 40);
        const page = Math.max(1, Math.min(50, parseInt(p.get('page') || '1', 10) || 1));
        data = q ? await search(q, page) : { items: [], more: false };
      } else if (u.pathname === '/api/ds/food') data = await food(p.get('idx') || '0', p.get('name') || '');
      else return new Response('not found', { status: 404 });
    } catch (e) { data = { error: String(e.message || e) }; status = 502; }

    const res = new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'public, max-age=86400' } });
    if (cache && status === 200 && u.pathname !== '/api/ds/ping') ctx.waitUntil(cache.put(key, res.clone()));
    for (const [k, v] of Object.entries(h)) res.headers.set(k, v);
    return res;
  },
};
