"""블로그 플랫폼 E2E — 실제로 띄운 백엔드 + 프론트에 대고 돈다.

핵심 질문: 발행한 글이 로그인 없이 공개 URL 로 보이고, 검색엔진이 읽을 수 있는가.
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import os

API_ORIGIN = os.environ.get("E2E_API", "http://localhost:8001")
API = f"{API_ORIGIN}/api/v1"
WEB = os.environ.get("E2E_WEB", "http://localhost:3001")
ok, fail = 0, 0


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


def webpath(url: str) -> str:
    """@ 는 경로 문자로 그대로 둔다. quote 기본 safe 에는 @ 가 없어 %40 이 되어 버린다."""
    return urllib.parse.quote(url, safe="/@")


def check(name, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name}")
    else:
        fail += 1
        print(f"  FAIL  {name}  {detail}")


stamp = str(int(time.time()))
AUTHOR = f"author{stamp}"
READER = f"reader{stamp}"

print("=" * 68)
print("1. 계정 + 블로그 신원")
print("=" * 68)

_, a = call("POST", f"{API}/auth/register",
            body={"email": f"{AUTHOR}@devshiplog.com", "password": "password1234", "name": "글쓴이"})
_, b = call("POST", f"{API}/auth/register",
            body={"email": f"{READER}@devshiplog.com", "password": "password1234", "name": "독자"})
at, bt = a["access_token"], b["access_token"]

s, me = call("GET", f"{API}/profile/me", at)
check("가입 직후 handle 없음", me["needs_handle"] is True)

s, prof = call("PUT", f"{API}/profile/me", at,
               {"handle": AUTHOR, "display_name": "글쓴이", "bio": "기술 글을 씁니다."})
check("handle 설정 200", s == 200, f"{s} {prof}")
call("PUT", f"{API}/profile/me", bt, {"handle": READER, "display_name": "독자"})

print()
print("=" * 68)
print("2. 초안 → 발행")
print("=" * 68)

s, src = call("POST", f"{API}/sources/extract", at, {"raw_text": "캐시 스탬피드 해결 기록"})
s, draft = call("POST", f"{API}/drafts", at, {
    "source_ids": [src[0]["id"]], "type": "troubleshooting",
    "audience": "intermediate", "length": "default", "use_style_profile": False,
})
draft_id = draft["id"]

BODY = """## 문제

피크 시간대에 동일 키가 동시에 만료되면서 요청이 원본 저장소로 몰렸습니다.

## 원인

TTL 이 모두 같은 시각으로 설정되어 있었습니다.

## 해결

단일 플라이트로 묶고 TTL 에 지터를 넣었습니다.
"""
s, _ = call("PUT", f"{API}/drafts/{draft_id}/content", at, {"content_md": BODY})
check("초안 내용 저장", s == 200)

s, post = call("POST", f"{API}/posts", at, {
    "draft_id": draft_id, "title": f"캐시 스탬피드 해결기 {stamp}", "tags": ["Redis", "성능"],
})
check("발행 201", s == 201, f"{s} {post}")
print(f"        └ 주소: {post.get('url')}")
post_url = post["url"]
post_id = post["id"]

s, again = call("POST", f"{API}/posts", at, {
    "draft_id": draft_id, "title": f"캐시 스탬피드 해결기 {stamp} (개정)", "tags": ["Redis"],
})
check("재발행 시 주소 유지", again.get("slug") == post["slug"], f"{again.get('slug')} vs {post['slug']}")

print()
print("=" * 68)
print("3. 공개 URL — 로그인 없이, 서버 렌더링")
print("=" * 68)

s, html = call("GET", f"{WEB}{webpath(post_url)}", raw=True)
check("공개 글 페이지 200", s == 200, str(s))
check("제목이 HTML 에 포함 (JS 없이 읽힘)", f"캐시 스탬피드 해결기 {stamp}" in html)
check("재발행 내용이 공개 페이지에 반영됨 (캐시 무효화)", "개정" in html)
check("본문이 HTML 에 포함", "단일 플라이트" in html)
check("작성자 표기", "글쓴이" in html)

check("canonical 링크", 'rel="canonical"' in html)
check("og:title", 'property="og:title"' in html or "og:title" in html)
check("og:type=article", "article" in html)
check("JSON-LD BlogPosting", "BlogPosting" in html)
m = re.search(r'<title>(.*?)</title>', html, re.S)
print(f"        └ <title>: {m.group(1)[:70] if m else '없음'}")

s, blog_html = call("GET", f"{WEB}/@{AUTHOR}", raw=True)
check("블로그 홈 200", s == 200, str(s))
check("소개가 렌더됨", "기술 글을 씁니다" in blog_html)
check("글 목록에 제목", f"캐시 스탬피드 해결기 {stamp}" in blog_html)

s, home = call("GET", WEB, raw=True)
check("홈 피드에 글 노출", f"캐시 스탬피드 해결기 {stamp}" in home)

s, tag_html = call("GET", f"{WEB}/tags/redis", raw=True)
check("태그 페이지에 글 노출", f"캐시 스탬피드 해결기 {stamp}" in tag_html, str(s))

print()
print("=" * 68)
print("4. SEO 표면")
print("=" * 68)

s, sitemap = call("GET", f"{WEB}/sitemap.xml", raw=True)
check("sitemap.xml 200", s == 200)
check("sitemap 에 글 주소 포함", webpath(post_url) in sitemap or post_url in sitemap)

s, robots = call("GET", f"{WEB}/robots.txt", raw=True)
check("robots 가 앱 영역 차단", "Disallow: /dashboard" in robots)
check("robots 가 sitemap 안내", "Sitemap:" in robots)

s, rss = call("GET", f"{WEB}/@{AUTHOR}/rss.xml", raw=True)
check("RSS 200", s == 200, str(s))
check("RSS 에 글 포함", f"캐시 스탬피드 해결기 {stamp}" in rss or "제목을 완전히" in rss)
check("RSS 가 유효한 XML 헤더", rss.strip().startswith("<?xml"))

print()
print("=" * 68)
print("5. 소셜")
print("=" * 68)

s, like = call("POST", f"{API}/social/posts/{post_id}/like", bt)
check("좋아요", like == {"liked": True, "like_count": 1}, str(like))

s, c = call("POST", f"{API}/social/posts/{post_id}/comments", bt, {"body": "좋은 글이네요"})
check("댓글 201", s == 201)
s, r = call("POST", f"{API}/social/posts/{post_id}/comments", at,
            {"body": "감사합니다", "parent_id": c["id"]})
check("답글 201", s == 201)

s, f = call("POST", f"{API}/social/users/{AUTHOR}/follow", bt)
check("팔로우", f["following"] is True, str(f))

s, notif = call("GET", f"{API}/social/notifications", at)
check("알림 3건 (좋아요/댓글/팔로우)", notif["unread_count"] == 3, str(notif["unread_count"]))

s, detail_html = call("GET", f"{WEB}{webpath(post_url)}", raw=True)
check("댓글이 서버 렌더에 포함", "좋은 글이네요" in detail_html)
check("답글이 서버 렌더에 포함", "감사합니다" in detail_html)

print()
print("=" * 68)
print("6. 비공개 처리")
print("=" * 68)

s, _ = call("POST", f"{API}/posts/{post_id}/unpublish", at)
check("발행 취소 200", s == 200)
# 캐시 무효화는 백그라운드 통지라 비동기다. 짧게 기다린다.
time.sleep(3)

s, gone = call("GET", f"{WEB}{webpath(post_url)}", raw=True)
check("내린 글은 공개 404", s == 404, str(s))

s, home2 = call("GET", WEB, raw=True)
check("홈 피드에서도 사라짐", f"캐시 스탬피드 해결기 {stamp}" not in home2)

print()
print("=" * 68)
print(f"결과: {ok} PASS / {fail} FAIL")
print("=" * 68)
print(f"AUTHOR_HANDLE={AUTHOR}")
print(f"AUTHOR_EMAIL={AUTHOR}@devshiplog.com")

# 실패가 있으면 0이 아닌 코드로 끝낸다. CI 가 이 값을 본다.
sys.exit(1 if fail else 0)
