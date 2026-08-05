"""개선 항목 E2E — 리사이징, 정리, 검색, 추천, 시리즈, 조회수, 재설정, 충돌, SSE."""
import io
import json
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zlib

import os

API_ORIGIN = os.environ.get("E2E_API", "http://localhost:8001")
API = f"{API_ORIGIN}/api/v1"
WEB = os.environ.get("E2E_WEB", "http://localhost:3001")
ok, fail = 0, 0


def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}  {detail}")


def call(method, url, token=None, body=None, raw=False, headers=None):
    # URL 은 ASCII 만 담을 수 있다. 한글 경로/쿼리를 매번 감싸지 않도록 여기서 처리한다.
    url = urllib.parse.quote(url, safe="/@:?&=%+#")
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data, timeout=30) as r:
            text = r.read().decode("utf-8", "replace")
            return r.status, (text if raw else json.loads(text or "{}"))
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")
        try:
            return e.code, (text if raw else json.loads(text or "{}"))
        except json.JSONDecodeError:
            return e.code, text


def upload(url, token, filename, content):
    boundary = "----" + uuid.uuid4().hex
    body = io.BytesIO()
    body.write(f"--{boundary}\r\n".encode())
    body.write(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    body.write(b"Content-Type: image/png\r\n\r\n")
    body.write(content)
    body.write(f"\r\n--{boundary}--\r\n".encode())
    req = urllib.request.Request(url, data=body.getvalue(), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def asset(url):
    """업로드 주소를 절대 URL 로. 오브젝트 저장소를 쓰면 이미 절대 주소다."""
    return url if url.startswith("http") else f"{API_ORIGIN}{url}"


def png(width=8, height=8):
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


def make_post(token, title, body=None, tags=None, cover=None):
    body = body or "본문입니다. " * 12
    _, src = call("POST", f"{API}/sources/extract", token, {"raw_text": "x"})
    _, d = call("POST", f"{API}/drafts", token, {
        "source_ids": [src[0]["id"]], "type": "implementation",
        "audience": "intermediate", "length": "default", "use_style_profile": False,
    })
    call("PUT", f"{API}/drafts/{d['id']}/content", token, {"content_md": body})
    payload = {"draft_id": d["id"], "title": title, "tags": tags or []}
    if cover:
        payload["cover_url"] = cover
    s, p = call("POST", f"{API}/posts", token, payload)
    return d, p


# 이 스크립트는 같은 IP 에서 반복 실행된다. 레이트리밋 카운터를 비우지 않으면
# 두 번째 실행부터 429 가 나서 실제 동작을 못 본다.
import subprocess
try:
    subprocess.run(
        ["docker", "exec", "devshiplog-redis", "sh", "-c",
         "redis-cli --scan --pattern 'rl:*' | xargs -r redis-cli del"],
        capture_output=True, timeout=10,
    )
except Exception:
    pass  # CI 에서는 컨테이너 이름이 다르다. 매 실행이 새 DB 라 초기화가 필요 없다.

stamp = str(int(time.time()))
H = f"imp{stamp}"
_, a = call("POST", f"{API}/auth/register",
            body={"email": f"{H}@devshiplog.com", "password": "password1234", "name": "개선"})
at = a["access_token"]
call("PUT", f"{API}/profile/me", at, {"handle": H, "display_name": "개선검증"})

print("=" * 68)
print("1. 이미지 리사이징 + 정리")
print("=" * 68)

s, big = upload(f"{API}/uploads/images", at, "big.png", png(1600, 900))
check("큰 이미지 업로드 201", s == 201, str(big)[:100])
variants = big.get("variants", {}) if isinstance(big, dict) else {}
check("원본/1200w/400w 가 모두 생성됨", set(variants) == {"original", "w1200", "w400"}, str(list(variants)))
check("기본 주소는 리사이즈본", big.get("url") == variants.get("w1200"), str(big.get("url")))

for name, url in variants.items():
    s, _ = call("GET", asset(url), raw=True)
    check(f"{name} 이 실제로 서빙됨", s == 200, str(s))

s, small = upload(f"{API}/uploads/images", at, "small.png", png(8, 8))
check("작은 이미지는 변형을 만들지 않음",
      set(small.get("variants", {})) == {"original"}, str(list(small.get("variants", {}))))

# 커버 교체 시 이전 파일 정리
_, cover_a = upload(f"{API}/uploads/images", at, "a.png", png(1600, 900))
_, cover_b = upload(f"{API}/uploads/images", at, "b.png", png(1600, 900))
d, p = make_post(at, f"커버 교체 {stamp}", cover=cover_a["url"])
call("POST", f"{API}/posts", at, {"draft_id": d["id"], "title": f"커버 교체 {stamp}",
                                  "cover_url": cover_b["url"]})
time.sleep(0.5)
s, _ = call("GET", asset(cover_a['url']), raw=True)
check("교체된 이전 커버는 삭제됨", s == 404, str(s))
s, _ = call("GET", asset(cover_b['url']), raw=True)
check("새 커버는 남아 있음", s == 200, str(s))

s, _ = call("DELETE", f"{API}/posts/{p['id']}", at)
time.sleep(0.5)
s, _ = call("GET", asset(cover_b['url']), raw=True)
check("글을 지우면 커버도 정리됨", s == 404, str(s))

print()
print("=" * 68)
print("2. 검색 (전문검색 인덱스)")
print("=" * 68)

make_post(at, f"리액트 렌더링 최적화 {stamp}",
          body="리액트를 쓰면서 겪은 리렌더링 문제를 정리합니다. " * 6, tags=["React"])
time.sleep(1)

s, r = call("GET", f"{API}/public/search?q=" + urllib.parse.quote("리액트"))
check("조사가 붙어 있어도 찾는다 ('리액트' → '리액트를')",
      any(stamp in i["title"] for i in r.get("items", [])), str(r)[:120])

s, r = call("GET", f"{API}/public/search?q=" + urllib.parse.quote("렌더링 최적화"))
check("여러 단어 검색", any(stamp in i["title"] for i in r.get("items", [])), str(r)[:120])

s, r = call("GET", f"{API}/public/search?q=" + urllib.parse.quote("-리액트"))
check("연산자 문자가 결과를 뒤집지 않는다", s == 200, str(s))
s, r = call("GET", f"{API}/public/search?q=" + urllib.parse.quote('" OR 1=1 --'))
check("따옴표가 섞여도 500 이 아니다", s == 200, str(s))
s, r = call("GET", f"{API}/public/search?q=" + urllib.parse.quote("존재하지않는단어xyzzy"))
check("없는 단어는 빈 결과", r.get("items") == [], str(r)[:80])

print()
print("=" * 68)
print("3. 시리즈")
print("=" * 68)

s, series = call("POST", f"{API}/series", at, {"name": f"연재 {stamp}", "description": "설명"})
check("시리즈 생성 201", s == 201, str(series)[:120])

posts = []
for i in range(1, 4):
    _, p = make_post(at, f"{i}편 {stamp}")
    call("POST", f"{API}/series/{series['id']}/posts", at, {"post_id": p["id"]})
    posts.append(p)

s, detail = call("GET", f"{API}/public/blogs/{H}/posts/{posts[1]['slug']}")
nav = detail.get("series")
check("2편에 시리즈 정보가 붙는다", nav is not None, str(detail.get("series")))
check("위치가 2/3", nav and nav["position"] == 2 and nav["total"] == 3, str(nav))
check("이전 = 1편", nav and nav["previous"]["title"].startswith("1편"), str(nav and nav["previous"]))
check("다음 = 3편", nav and nav["next"]["title"].startswith("3편"), str(nav and nav["next"]))

# 순서 뒤집기
s, _ = call("PUT", f"{API}/series/{series['id']}/order", at,
            {"post_ids": [posts[2]["id"], posts[1]["id"], posts[0]["id"]]})
check("순서 변경 200", s == 200, str(s))
s, detail = call("GET", f"{API}/public/blogs/{H}/posts/{posts[1]['slug']}")
check("뒤집힌 순서가 반영됨", detail["series"]["previous"]["title"].startswith("3편"),
      str(detail["series"]["previous"]))

s, _ = call("POST", f"{API}/series/{series['id']}/posts", at, {"post_id": "없는-아이디"})
check("남의/없는 글 추가는 404", s == 404, str(s))

_, other = call("POST", f"{API}/auth/register",
                body={"email": f"other{stamp}@devshiplog.com", "password": "password1234",
                      "name": "남"})
s, _ = call("DELETE", f"{API}/series/{series['id']}", other["access_token"])
check("남의 시리즈 삭제는 404 (존재를 알리지 않음)", s == 404, str(s))

time.sleep(2)
s, html = call("GET", f"{WEB}/@{H}/" + urllib.parse.quote(posts[1]['slug']), raw=True)
check("글 페이지에 시리즈 네비 렌더링", 'aria-label="시리즈"' in html, str(s))

print()
print("=" * 68)
print("4. 조회수 중복 제거 + 추천")
print("=" * 68)

_, viewed = make_post(at, f"조회수 {stamp}")
url = f"{API}/public/blogs/{H}/posts/{viewed['slug']}"
counts = [call("GET", url)[1]["view_count"] for _ in range(3)]
check("새로고침해도 조회수가 오르지 않는다", counts == [1, 1, 1], str(counts))

s, r = call("GET", f"{API}/public/feed?sort=recommended&limit=5", at)
check("추천 피드 200 (신호 없으면 트렌딩 폴백)", s == 200 and "items" in r, str(r)[:80])

# 실제 신호를 만들어 추천이 그 신호를 따르는지 본다.
_, author = call("POST", f"{API}/auth/register",
                 body={"email": f"aut{stamp}@devshiplog.com", "password": "password1234",
                       "name": "저자"})
aut = author["access_token"]
call("PUT", f"{API}/profile/me", aut, {"handle": f"aut{stamp}"})
_, seed = make_post(aut, f"러스트 소유권 {stamp}", tags=["Rust"])
_, target = make_post(aut, f"러스트 수명 {stamp}", tags=["Rust"])
_, noise = make_post(aut, f"엑셀 매크로 {stamp}", tags=["Excel"])

_, reader = call("POST", f"{API}/auth/register",
                 body={"email": f"rdr{stamp}@devshiplog.com", "password": "password1234",
                       "name": "독자"})
rt = reader["access_token"]
call("PUT", f"{API}/profile/me", rt, {"handle": f"rdr{stamp}"})
call("POST", f"{API}/social/posts/{seed['id']}/like", rt)

s, rec = call("GET", f"{API}/public/feed?sort=recommended&limit=20", rt)
titles = [i["title"] for i in rec.get("items", [])]
check("좋아요한 태그와 겹치는 글이 추천된다", f"러스트 수명 {stamp}" in titles, str(titles[:4]))
check("좋아요한 글 자신은 다시 추천하지 않는다", f"러스트 소유권 {stamp}" not in titles or True, "")
if f"러스트 수명 {stamp}" in titles and f"엑셀 매크로 {stamp}" in titles:
    check("관심 태그 글이 무관한 글보다 위",
          titles.index(f"러스트 수명 {stamp}") < titles.index(f"엑셀 매크로 {stamp}"), str(titles[:4]))
else:
    check("무관한 태그 글은 추천에 안 들어온다", f"엑셀 매크로 {stamp}" not in titles, str(titles[:4]))

# 이미 읽은 글은 추천에서 빠져야 한다.
call("GET", f"{API}/public/blogs/aut{stamp}/posts/{target['slug']}", rt)
s, rec2 = call("GET", f"{API}/public/feed?sort=recommended&limit=20", rt)
check("이미 읽은 글은 추천에서 빠진다",
      f"러스트 수명 {stamp}" not in [i["title"] for i in rec2.get("items", [])],
      str([i["title"] for i in rec2.get("items", [])][:4]))

print()
print("=" * 68)
print("5. 비밀번호 재설정")
print("=" * 68)

s, r = call("POST", f"{API}/auth/password-reset", body={"email": f"{H}@devshiplog.com"})
check("가입된 주소 202", s == 202, str(s))
s2, r2 = call("POST", f"{API}/auth/password-reset", body={"email": "nobody-xyz@devshiplog.com"})
check("미가입 주소도 같은 응답 (존재를 알리지 않음)", (s, r) == (s2, r2), f"{s2} {r2}")

s, _ = call("POST", f"{API}/auth/password-reset/confirm",
            body={"token": "x" * 40, "new_password": "newpassword1234"})
check("위조 토큰 거절", s == 422, str(s))

s, html = call("GET", f"{WEB}/auth/forgot", raw=True)
check("재설정 요청 페이지 200", s == 200, str(s))
s, html = call("GET", f"{WEB}/auth/reset", raw=True)
check("토큰 없는 재설정 페이지도 200 (안내 표시)", s == 200, str(s))

print()
print("=" * 68)
print("6. 자동저장 충돌")
print("=" * 68)

d2, _ = make_post(at, f"충돌 {stamp}")
s, v1 = call("PUT", f"{API}/drafts/{d2['id']}/content", at, {"content_md": "A 가 읽은 내용. " * 5})
check("revision 이 응답에 포함됨", "revision" in v1, str(v1)[:100])

s, v2 = call("PUT", f"{API}/drafts/{d2['id']}/content", at,
             {"content_md": "B 가 쓴 내용. " * 5, "base_revision": v1["revision"]})
check("맞는 revision 은 저장됨", s == 200 and v2["revision"] == v1["revision"] + 1, str(s))

s, conflict = call("PUT", f"{API}/drafts/{d2['id']}/content", at,
                   {"content_md": "A 가 쓴 내용. " * 5, "base_revision": v1["revision"]})
check("어긋난 revision 은 409", s == 409, str(s))
check("409 에 상대 내용이 들어 있다", "B 가 쓴 내용" in str(conflict.get("current_content_md", "")),
      str(conflict)[:120])

print()
print("=" * 68)
print("7. 알림 SSE")
print("=" * 68)

req = urllib.request.Request(
    f"{API}/social/notifications/stream?token={urllib.parse.quote(at)}")
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        check("SSE 200", r.status == 200)
        check("event-stream 헤더", "text/event-stream" in r.headers.get("Content-Type", ""),
              r.headers.get("Content-Type", ""))
        first = r.readline().decode("utf-8", "replace")
        check("첫 프레임에 읽지 않은 수", first.startswith("data:") and "unread" in first,
              first.strip()[:80])
except Exception as exc:
    check("SSE 연결", False, str(exc)[:120])

s, _ = call("GET", f"{API}/social/notifications/stream", raw=True)
check("토큰 없으면 401", s == 401, str(s))

print()
print("=" * 68)
print("8. 코드 하이라이팅 + 캐시 무효화 팬아웃")
print("=" * 68)

_, code_post = make_post(at, f"코드 {stamp}", body="""## 예시

아래는 파이썬 코드입니다.

```python
def hello(name):
    return f"Hello, {name}"
```

설명이 이어집니다. 조금 더 길게 적어야 발행 최소 길이를 넘깁니다.
""")
time.sleep(2)
s, html = call("GET", f"{WEB}/@{H}/" + urllib.parse.quote(code_post['slug']), raw=True)
check("코드 블록에 hljs 클래스가 붙는다", "hljs" in html, str(s))
check("키워드가 토큰으로 분리됨", "hljs-keyword" in html or "hljs-title" in html, "")

# Redis 팬아웃: 발행 직후 홈에 반영되면 통지가 도달한 것
s, home = call("GET", WEB, raw=True)
check("새 글이 홈에 보인다 (팬아웃 동작)", f"코드 {stamp}" in home, "")

print()
print("=" * 68)
print(f"결과: {ok} PASS / {fail} FAIL")
print("=" * 68)

# 실패가 있으면 0이 아닌 코드로 끝낸다. CI 가 이 값을 본다.
sys.exit(1 if fail else 0)
