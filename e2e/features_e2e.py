"""새로 붙인 기능 E2E — 업로드, 피드 정렬/기간, 목차, 커버 이미지."""
import io
import json
import struct
import sys
import time
import urllib.error
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


def call(method, url, token=None, body=None, raw=False):
    req = urllib.request.Request(url, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
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


def upload(url, token, filename, content, mime="image/png"):
    boundary = "----" + uuid.uuid4().hex
    body = io.BytesIO()
    body.write(f"--{boundary}\r\n".encode())
    body.write(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    body.write(f"Content-Type: {mime}\r\n\r\n".encode())
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
    """진짜 PNG 를 만든다 — 매직바이트 검사를 통과해야 하므로."""
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


stamp = str(int(time.time()))
H = f"feat{stamp}"

print("=" * 68)
print("1. 이미지 업로드")
print("=" * 68)

_, a = call("POST", f"{API}/auth/register",
            body={"email": f"{H}@devshiplog.com", "password": "password1234", "name": "기능"})
at = a["access_token"]
call("PUT", f"{API}/profile/me", at, {"handle": H, "display_name": "기능검증"})

s, up = call("POST", f"{API}/uploads/images", at)  # 파일 없이
check("파일 없으면 422", s == 422, str(s))

s, up = upload(f"{API}/uploads/images", at, "a.png", png())
check("PNG 업로드 201", s == 201, str(up)[:120])
image_url = up.get("url", "") if isinstance(up, dict) else ""
print(f"        └ {image_url}")

s, _ = call("GET", asset(image_url), raw=True)
check("업로드한 파일이 실제로 서빙됨", s == 200, str(s))

s, bad = upload(f"{API}/uploads/images", at, "evil.png", b"<?php system($_GET[0]); ?>" * 4)
check("확장자만 png 인 위조 파일 거부", s == 400, str(s))

s, bad = upload(f"{API}/uploads/images", at, "../../etc/passwd.png", png())
check("경로 탈출 파일명도 안전하게 처리", s == 201 and ".." not in str(bad), str(bad)[:80])

s, big = upload(f"{API}/uploads/images", at, "big.png", png(1, 1) + b"\x00" * (6 * 1024 * 1024))
check("용량 초과 거부(413)", s == 413, str(s))

s, anon = upload(f"{API}/uploads/images", "", "a.png", png())
check("비로그인 업로드 거부", s in (401, 403), str(s))

s, av = upload(f"{API}/uploads/avatar", at, "me.png", png())
check("아바타 업로드 201", s == 201, str(av)[:120])
s, prof = call("GET", f"{API}/profile/me", at)
check("아바타가 프로필에 반영됨", bool(prof.get("avatar_url")), str(prof.get("avatar_url")))

print()
print("=" * 68)
print("2. 커버 이미지 + 목차")
print("=" * 68)

_, src = call("POST", f"{API}/sources/extract", at, {"raw_text": "목차 검증"})
_, d = call("POST", f"{API}/drafts", at, {
    "source_ids": [src[0]["id"]], "type": "implementation",
    "audience": "intermediate", "length": "default", "use_style_profile": False,
})
BODY = """## 배경

왜 이 문제를 봤는지 적습니다.

```python
# 이건 제목이 아니라 코드 주석입니다
## 여기도 마찬가지
```

## 접근

첫 번째 시도를 적습니다.

### 세부 단계

더 들어간 내용입니다.

## 배경

같은 제목이 두 번 나오는 경우입니다.
"""
call("PUT", f"{API}/drafts/{d['id']}/content", at, {"content_md": BODY})
s, post = call("POST", f"{API}/posts", at, {
    "draft_id": d["id"], "title": f"목차 검증 {stamp}", "tags": ["목차"],
    "cover_url": image_url,
})
check("커버 이미지와 함께 발행 201", s == 201, str(post)[:160])
check("커버가 응답에 반영됨", post.get("cover_url") == image_url, str(post.get("cover_url")))
s, bad = call("POST", f"{API}/posts", at, {
    "draft_id": d["id"], "title": "나쁜 커버", "cover_url": "javascript:alert(1)"})
check("javascript: 커버 거부", s == 422, str(s))
s, bad = call("POST", f"{API}/posts", at, {
    "draft_id": d["id"], "title": "나쁜 커버", "cover_url": "http://tracker.example/px.gif"})
check("평문 http 외부 커버 거부", s == 422, str(s))

path = post["url"].replace("@", "%40") if False else post["url"]
s, html = call("GET", f"{WEB}{urllib.parse.quote(path, safe='/@')}", raw=True)
check("글 페이지 200", s == 200, str(s))
check("목차가 서버 HTML 에 있음", 'aria-label="목차"' in html, "")
check("제목에 앵커 id 부여", 'id="배경"' in html, "")
check("중복 제목은 번호로 구분", 'id="배경-1"' in html, "")
check("h3 도 목차에", 'id="세부-단계"' in html, "")
check("코드블록 주석은 목차에 없음", "이건 제목이 아니라" not in html.split('aria-label="목차"')[1][:900], "")
check("플로팅 좋아요 바 존재", 'aria-label="좋아요"' in html, "")

time.sleep(3)  # 캐시 무효화는 백그라운드 통지다
s, home = call("GET", WEB, raw=True)
check("홈 카드에 썸네일 이미지", image_url.split("/")[-1] in home, "")
# 오브젝트 저장소를 쓰면 브라우저가 그쪽으로 직접 받는다 (프론트 프록시를 안 탄다).
# 로컬 디스크 백엔드일 때만 /uploads 리라이트가 필요하다.
if image_url.startswith("http"):
    s, _ = call("GET", image_url, raw=True)
    check("오브젝트 저장소에서 직접 열림", s == 200, str(s))
else:
    s, _ = call("GET", f"{WEB}{image_url}", raw=True)
    check("프론트에서도 이미지가 열림 (프록시)", s == 200, str(s))

print()
print("=" * 68)
print("3. 피드 탭 + 기간 필터")
print("=" * 68)

for sort in ["trending", "recommended", "recent", "following"]:
    s, r = call("GET", f"{API}/public/feed?sort={sort}&limit=5")
    check(f"백엔드 sort={sort} 200", s == 200 and "items" in r, str(r)[:80])

for period in ["week", "month", "year", "all"]:
    s, r = call("GET", f"{API}/public/feed?sort=trending&period={period}&limit=5")
    check(f"백엔드 period={period} 200", s == 200, str(r)[:80])

s, r = call("GET", f"{API}/public/feed?sort=nope")
check("모르는 정렬은 422", s == 422, str(s))
s, r = call("GET", f"{API}/public/feed?sort=trending&period=nope")
check("모르는 기간은 422", s == 422, str(s))

for sort, label in [("trending", "트렌딩"), ("recommended", "추천"),
                    ("recent", "최신"), ("following", "피드")]:
    q = "" if sort == "recent" else f"?sort={sort}"
    s, h = call("GET", f"{WEB}/{q}", raw=True)
    marker = f'href="/{q}"' if q else 'href="/"'
    check(f"홈 {label} 탭 200 + 현재 탭 표시", s == 200 and 'aria-current="page"' in h, str(s))

s, h = call("GET", f"{WEB}/?sort=trending", raw=True)
check("트렌딩에서 기간 필터 노출", 'aria-label="기간"' in h)
s, h = call("GET", f"{WEB}/?sort=recent", raw=True)
check("최신에서는 기간 필터 숨김", 'aria-label="기간"' not in h)
s, h = call("GET", f"{WEB}/?sort=hack&period=hack", raw=True)
check("이상한 쿼리는 기본값으로 처리 (500 아님)", s == 200, str(s))

s, h = call("GET", f"{WEB}/?sort=following", raw=True)
check("비로그인 피드 탭도 200", s == 200, str(s))

print()
print("=" * 68)
print(f"결과: {ok} PASS / {fail} FAIL")
print("=" * 68)

# 실패가 있으면 0이 아닌 코드로 끝낸다. CI 가 이 값을 본다.
sys.exit(1 if fail else 0)
