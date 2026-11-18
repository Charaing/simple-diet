# 식단

검은 배경에 흰 글씨의 단순한 식단 기록 앱.

- **오늘** — 먹은 칼로리 / 기초대사량, 먹은 음식 목록, 체중 기록
- **계획** — 먹을 음식을 체크리스트로 적어두고, 먹으면 체크 → 오늘 칼로리에 반영
- 음식 검색: 일반 음식 1.8만 개 + 편의점·가공식품 31만 개, 몇 g당 몇 kcal인지 직접 고치기, 내 음식 저장
- 기초대사량: Mifflin-St Jeor 공식, 그날 기록한 체중으로 다시 계산
- 기록은 브라우저(localStorage)에만 저장

## 실행

웹에서 바로: GitHub Pages 주소로 열기

칼로리 사전 검색은 Cloudflare Worker(`worker/`)로 돼서 따로 켤 건 없어요. 내 컴퓨터에서 직접 열고 싶으면:

```bash
python server.py
```

→ http://localhost:5178 (Windows는 `start.bat` 더블클릭)

Worker와 `server.py`는 앱에서 검색할 때만 칼로리 사전에 한 번씩 물어보고 결과를 캐시합니다. Worker 배포 방법은 `worker/README.md`.

## 데이터 · 출처

- `foods.js`, `packaged.js` — [Charaing/hankki-daily](https://github.com/Charaing/hankki-daily)(MIT)의 `data/`를 `build_foods.py`로 압축. 원 데이터는 식품의약품안전처 식품영양성분 DB, 농촌진흥청 국가표준식품성분표.
- `fonts/PretendardVariable.woff2` — [Pretendard](https://github.com/orioncactus/pretendard), SIL Open Font License 1.1 (`fonts/Pretendard-LICENSE.txt`)
- 칼로리 사전 검색 결과 — [다이어트신](https://www.dietshin.com/calorie/calorie_main.asp). 데이터를 저장소에 넣지 않고 검색할 때만 조회합니다.

데이터 다시 만들기:

```bash
python build_foods.py <hankki-daily 폴더> .
```
