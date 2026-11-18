"""식단 앱 로컬 서버.
 - 이 폴더의 파일(index.html 등)을 그대로 보여준다.
 - /api/ds/search?q=..&page=N : 다이어트신 칼로리 사전 검색 결과(20개씩)
 - /api/ds/food?idx=..        : 음식 1인분 기준량
사용자가 앱에서 검색할 때만 한 번씩 물어보고, 결과는 메모리에 캐시한다.
실행: python server.py  →  http://localhost:5178
"""
import html, json, re, sys, threading, time, urllib.parse, urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE = 'https://www.dietshin.com/calorie/'
UA = 'Mozilla/5.0 (personal diet app; on-demand lookup)'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5178
cache, lock, last = {}, threading.Lock(), [0.0]


HEADERS = {'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml', 'Accept-Language': 'ko-KR,ko;q=0.9',
           'Cache-Control': 'no-cache', 'Pragma': 'no-cache'}


def get(url, check):
    """check(text) 가 참일 때만 결과로 인정(다른 검색어 페이지가 섞여 오는 경우 방지)."""
    if url in cache:
        return cache[url]
    with lock:  # 한 번에 하나씩, 최소 1초 간격
        if url in cache:
            return cache[url]
        for _ in range(2):
            wait = 1.0 - (time.time() - last[0])
            if wait > 0:
                time.sleep(wait)
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                text = r.read().decode('utf-8', 'replace')
            last[0] = time.time()
            if check(text):
                cache[url] = text
                return text
        raise RuntimeError('칼로리 사전 응답이 검색어와 맞지 않아요')


strip = lambda s: html.unescape(re.sub(r'<[^>]+>', '', s)).strip()
ROW = re.compile(r'calorie-foodview\.asp\?cal_idx=(\d+)&cal_type=F">(.*?)</a></td>\s*<td>\s*([\d.,]+)\s*kcal', re.S)


def search(q, page):
    url = BASE + 'calorie_search.asp?keyword=' + urllib.parse.quote(q) + (f'&gotopage={page}' if page > 1 else '')
    # 검색 결과 이름마다 검색어가 빨간색으로 표시됨 → 그게 있거나 결과가 없을 때만 인정
    t = get(url, lambda t: 'calorie-foodview' not in t or f"<font color='red'>{html.escape(q)}</font>" in t)
    items = []
    for idx, name, kcal in ROW.findall(t):
        name = strip(name)
        m = re.match(r'^\[([^\]]+)\]\s*(.*)$', name)
        brand, name = (m.group(1), m.group(2)) if m else ('', name)
        items.append({'idx': idx, 'n': name, 'b': brand, 'kcal': float(kcal.replace(',', ''))})
    more = f'gotopage={page + 1}"' in t
    return {'items': items, 'more': more}


def food(idx, name=''):
    t = get(BASE + f'calorie-foodview.asp?cal_idx={int(idx)}&cal_type=F', lambda t: not name or name.replace(' ', '') in re.sub(r'\s+', '', strip(t)))
    flat = re.sub(r'\s+', ' ', strip(t))
    m = re.search(r'(\d[\d.]*\s*\S{0,4}?)\s*\(\s*([\d.,]+)\s*(g|ml|mL|kg|L)\s*\)\s*칼로리\s*([\d.,]+)\s*kcal', flat)
    if m:
        amt, unit = float(m.group(2).replace(',', '')), m.group(3).lower()
        if unit == 'kg': amt, unit = amt * 1000, 'g'
        if unit == 'l': amt, unit = amt * 1000, 'ml'
        return {'label': m.group(1).strip(), 'amount': amt, 'unit': unit, 'kcal': float(m.group(4).replace(',', ''))}
    m = re.search(r'(\S{1,12})\s*칼로리\s*([\d.,]+)\s*kcal', flat)
    return {'label': m.group(1) if m else '1인분', 'amount': None, 'unit': None, 'kcal': float(m.group(2).replace(',', '')) if m else None}


class H(SimpleHTTPRequestHandler):
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if not u.path.startswith('/api/ds/'):
            return super().do_GET()
        p = urllib.parse.parse_qs(u.query)
        try:
            if u.path == '/api/ds/search':
                q = (p.get('q') or [''])[0].strip()[:40]
                page = max(1, min(50, int((p.get('page') or ['1'])[0])))
                data = search(q, page) if q else {'items': [], 'more': False}
            elif u.path == '/api/ds/food':
                data = food((p.get('idx') or ['0'])[0], (p.get('name') or [''])[0])
            else:
                return self.send_error(404)
            body, code = json.dumps(data, ensure_ascii=False).encode(), 200
        except Exception as e:
            body, code = json.dumps({'error': str(e)}).encode(), 502
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f'http://localhost:{PORT}')
    ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
