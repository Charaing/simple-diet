"""hankki-daily(https://github.com/Charaing/hankki-daily) data/ 폴더에서 앱용 음식 데이터를 만든다.
사용: python build_foods.py <hankki-daily 폴더> <출력 폴더>
 - foods.js    : 일반 음식·식재료 (window.FOODS)
 - packaged.js : 편의점·가공식품 (window.PACK, 탭 구분 텍스트)
행 형식: 이름, kcal(100g 또는 100ml당), 단위, 1회 제공량
"""
import glob, json, os, re, sys

src, out = sys.argv[1], sys.argv[2]
clean = lambda s: re.sub(r'\s+', ' ', (s or '').replace('﻿', '').replace('_', ' ')).strip()
key = lambda s: re.sub(r'\s+', '', s)
serving = lambda r: (round(r[7], 1) if r[7] % 1 else int(r[7])) if r[7] and r[7] > 0 else 100
pref = lambda r: (0 if r[6] == 'g' else 30) + (100 if '급식' in r[10] else 0) + (-20 if '가정식' in r[10] else 0) + (-10 if r[0].startswith('RDA') else 0)

generic, packed, brands, blist = {}, {}, {}, []
for f in sorted(glob.glob(os.path.join(src, 'data', 'foods-*.json'))):
    for r in json.load(open(f, encoding='utf8')):
        if not r[2] or r[2] < 0: continue
        name = clean(r[1])
        if not name: continue
        if r[0].startswith('P'):
            b = re.sub(r'^(주식회사|\(주\)|㈜|\(유\)|유한회사)\s*|\s*(주식회사|\(주\)|㈜)$', '', clean(r[9])).strip()
            k = (key(name), b)
            if k in packed: continue
            if b not in brands: brands[b] = len(blist); blist.append(b)
            packed[k] = f"{name}\t{brands[b]}\t{round(r[2])}\t{'m' if r[6] == 'ml' else ''}\t{serving(r)}"
        else:
            k = key(name)
            if k not in generic or pref(r) < pref(generic[k]): generic[k] = r

rows = sorted(([clean(r[1]), round(r[2]), r[6], serving(r)] for r in generic.values()), key=lambda x: len(x[0]))
open(os.path.join(out, 'foods.js'), 'w', encoding='utf8').write(
    'window.FOODS=' + json.dumps(rows, ensure_ascii=False, separators=(',', ':')) + ';')
lines = sorted(packed.values(), key=lambda s: len(s.split('\t', 1)[0]))
open(os.path.join(out, 'packaged.js'), 'w', encoding='utf8').write(
    'window.PACK={b:' + json.dumps(blist, ensure_ascii=False, separators=(',', ':')) + ',d:' + json.dumps('\n'.join(lines), ensure_ascii=False) + '};')
print(len(rows), 'generic /', len(lines), 'packaged')
