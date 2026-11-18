# 칼로리 사전 Worker

`start.bat` 없이, 폰에서도 칼로리 사전 검색이 되게 하는 Cloudflare Worker예요. (무료 플랜으로 충분)

## 올리는 법 (웹에서, 설치 없이)

1. https://dash.cloudflare.com 에 가입·로그인
2. 왼쪽 **Workers & Pages** → **Create** → **Create Worker** (Hello World 템플릿)
3. 이름을 `simple-diet-ds` 로 하고 **Deploy**
4. **Edit code** → 기본 코드를 지우고 [`worker.js`](worker.js) 내용을 통째로 붙여넣기 → **Deploy**
5. 주소 확인: `https://simple-diet-ds.<내 이름>.workers.dev/api/ds/ping` 을 열어서 `{"ok":true}` 가 나오면 성공

## 앱에 연결

`index.html` 에서 이 줄에 Worker 주소를 넣고 GitHub에 올리면 끝.

```js
const DS_WORKER='https://simple-diet-ds.<내 이름>.workers.dev';
```

## 명령어로 올리기 (선택)

```bash
cd worker
npx wrangler login
npx wrangler deploy
```

## 참고

- 앱에서 검색할 때만 칼로리 사전에 한 번씩 물어보고, 같은 검색은 하루 동안 캐시해요.
- `https://charaing.github.io` 와 `localhost` 에서 연 앱만 쓸 수 있게 막아뒀어요. 다른 주소에서 쓰려면 `worker.js` 의 `ALLOW` 에 추가하세요.
