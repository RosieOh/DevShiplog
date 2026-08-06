"""신선도 E2E — 이 제품의 차별점이 실제로 도는지.

발행 → 스택 자동 추출 → 공개 페이지 배지 → 독자 신호 → 작성자 갱신 목록 → 검증 →
목록에서 사라짐. 이 한 바퀴가 돌지 않으면 나머지는 의미가 없다.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

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
    url = urllib.parse.quote(url, safe="/@:?&=%+#")
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


stamp = str(int(time.time()))
AUTHOR = f"fresh{stamp}"
READER = f"reader{stamp}"

_, a = call("POST", f"{API}/auth/register",
            body={"email": f"{AUTHOR}@devshiplog.com", "password": "password1234", "name": "글쓴이"})
_, b = call("POST", f"{API}/auth/register",
            body={"email": f"{READER}@devshiplog.com", "password": "password1234", "name": "독자"})
at, bt = a["access_token"], b["access_token"]
call("PUT", f"{API}/profile/me", at, {"handle": AUTHOR, "display_name": "글쓴이"})
call("PUT", f"{API}/profile/me", bt, {"handle": READER, "display_name": "독자"})


def make_post(title, body, stacks=None):
    _, src = call("POST", f"{API}/sources/extract", at, {"raw_text": "x"})
    _, d = call("POST", f"{API}/drafts", at, {
        "source_ids": [src[0]["id"]], "type": "implementation",
        "audience": "intermediate", "length": "default", "use_style_profile": False,
    })
    call("PUT", f"{API}/drafts/{d['id']}/content", at, {"content_md": body})
    payload = {"draft_id": d["id"], "title": title}
    if stacks is not None:
        payload["stacks"] = stacks
    return call("POST", f"{API}/posts", at, payload)[1]


print("=" * 68)
print("1. 발행하면 본문에서 스택을 뽑는다")
print("=" * 68)

BODY = """## 배경

React 18 에서 리렌더링 문제를 겪었습니다.

```json
{ "dependencies": { "react": "^18.3.1", "next": "14.2.0" } }
```

```python
import fastapi
```

본문이 충분히 길어야 발행됩니다. """ + "설명이 이어집니다. " * 10

old_post = make_post(f"낡은 글 {stamp}", BODY)
found = {s["name"]: s["version"] for s in old_post.get("stacks", [])}
check("package.json 에서 react 18.3", found.get("react") == "18.3", str(found))
check("next 14.2 도 함께", found.get("nextjs") == "14.2", str(found))
check("코드 펜스에서 python", "python" in found, str(found))
check("패치 버전은 버린다 (18.3.1 → 18.3)", found.get("react") == "18.3", str(found))

print()
print("=" * 68)
print("2. 공개 페이지에 전제와 신선도가 보인다")
print("=" * 68)

time.sleep(2.5)
url = f"/@{AUTHOR}/{old_post['slug']}"
s, html = call("GET", f"{WEB}{url}", raw=True)
check("글 페이지 200", s == 200, str(s))
check("스택 배지가 HTML 에 있다", 'aria-label="이 글이 전제하는 기술 스택"' in html)
check("react@18.3 이 보인다", "18.3" in html and "react" in html)
check("신선도 경고가 뜬다", "메이저 버전이 나왔습니다" in html or "동작 확인이 없었" in html,
      "React 18 은 19 보다 뒤처졌으므로 경고가 나와야 한다")
check("“따라 해보셨나요?” 가 있다", "따라 해보셨나요" in html)

s, detail = call("GET", f"{API}/public/blogs/{AUTHOR}/posts/{old_post['slug']}")
check("API 신선도 레벨이 stale/aging", detail["freshness"]["level"] in ("stale", "aging"),
      detail["freshness"]["level"])
check("뒤처진 스택을 짚어준다",
      any(o["name"] == "react" for o in detail["freshness"]["outdated"]),
      str(detail["freshness"]["outdated"]))
check("검증 이력이 없다", detail["freshness"]["verified_at"] is None)

print()
print("=" * 68)
print("3. 목록에서도 클릭 전에 구분된다")
print("=" * 68)

s, feed = call("GET", f"{API}/public/feed?limit=5")
item = next((i for i in feed["items"] if i["title"].startswith("낡은 글")), None)
check("피드 카드에 신선도", item and item["freshness"]["level"] in ("stale", "aging"),
      str(item and item["freshness"]["level"]))
check("피드 카드에 스택", item and any(st["name"] == "react" for st in item["stacks"]),
      str(item and item["stacks"]))

print()
print("=" * 68)
print("4. 스택으로 탐색한다")
print("=" * 68)

s, by_stack = call("GET", f"{API}/public/stacks/react")
check("react 글 목록 200", s == 200 and by_stack["items"], str(s))
s, by_version = call("GET", f"{API}/public/stacks/react?version=18")
check("18 로 좁히면 18.x 가 잡힌다",
      any(i["title"].startswith("낡은 글") for i in by_version["items"]),
      str([i["title"] for i in by_version["items"]]))
s, by_version = call("GET", f"{API}/public/stacks/react?version=19")
check("19 로 좁히면 안 잡힌다",
      not any(i["title"].startswith("낡은 글") for i in by_version["items"]), "")
s, popular = call("GET", f"{API}/public/stacks")
check("인기 스택 집계", any(x["name"] == "react" for x in popular), str(popular[:3]))

s, page = call("GET", f"{WEB}/stacks/react", raw=True)
check("스택 페이지가 렌더된다", s == 200 and "기술 스택" in page, str(s))
check("정렬 기본값이 검증 최신순", "검증 최신순" in page)

print()
print("=" * 68)
print("5. 독자가 “안 됐어요” 를 보낸다")
print("=" * 68)

s, sig = call("POST", f"{API}/posts/{old_post['id']}/signal", bt,
              {"kind": "broken", "note": "Node 22 에서는 이 옵션이 없어졌습니다"})
check("신호 전송 200", s == 200, str(sig))
check("broken 1건으로 집계", sig.get("broken") == 1, str(sig))

s, sig2 = call("POST", f"{API}/posts/{old_post['id']}/signal", bt, {"kind": "works"})
check("마음이 바뀌면 덮어쓴다 (수가 안 부푼다)",
      sig2 == {"works": 1, "broken": 0, "my_signal": "works"}, str(sig2))
call("POST", f"{API}/posts/{old_post['id']}/signal", bt, {"kind": "broken"})

s, _ = call("POST", f"{API}/posts/{old_post['id']}/signal", at, {"kind": "works"})
check("자기 글에는 신호를 못 보낸다", s == 422, str(s))

print()
print("=" * 68)
print("6. 작성자 갱신 목록 → 검증 → 사라짐")
print("=" * 68)

fresh_post = make_post(f"최신 글 {stamp}", BODY, stacks=[{"name": "react", "version": "19.0"}])
call("POST", f"{API}/posts/{fresh_post['id']}/verify", at)

s, todo = call("GET", f"{API}/posts/needs-update", at)
titles = [i["title"] for i in todo["items"]]
check("낡은 글이 갱신 목록에 있다", any(t.startswith("낡은 글") for t in titles), str(titles))
check("방금 검증한 글은 없다", not any(t.startswith("최신 글") for t in titles), str(titles))
check("안 되는 글이 맨 위", titles and titles[0].startswith("낡은 글"), str(titles))

s, done = call("POST", f"{API}/posts/{old_post['id']}/verify", at)
check("검증 200", s == 200 and done.get("verified_at"), str(done))

s, detail = call("GET", f"{API}/public/blogs/{AUTHOR}/posts/{old_post['slug']}")
check("검증 시각이 공개 페이지에 반영", detail["freshness"]["verified_at"] is not None)
check("처리된 신호는 더 이상 세지 않는다", detail["signals"]["broken"] == 0,
      str(detail["signals"]))
check("그래도 React 18 이라 경고는 남는다",
      detail["freshness"]["level"] in ("aging", "stale"), detail["freshness"]["level"])

# 검증했어도 React 18 이면 목록에는 남는다 (스택이 실제로 뒤처졌으므로).
# 바뀌어야 하는 것은 "급함" 표시다 — 안 된다는 신고가 처리됐다.
s, todo = call("GET", f"{API}/posts/needs-update", at)
entry = next((i for i in todo["items"] if i["title"].startswith("낡은 글")), None)
check("검증 후에도 목록에 남는다 (스택이 뒤처졌으므로)", entry is not None, "")
check("더 이상 급하지 않다 (신고가 처리됨)",
      entry and entry["signals"]["broken"] == 0, str(entry and entry["signals"]))

print()
print("=" * 68)
print("7. 소개 페이지가 문제를 말한다")
print("=" * 68)

s, about = call("GET", f"{WEB}/about", raw=True)
check("소개 페이지 200", s == 200, str(s))
check("문제부터 말한다", "틀린 글" in about)
check("AI 자랑으로 시작하지 않는다", about.index("틀린 글") < about.find("초안"))

print()
print("=" * 68)
print(f"결과: {ok} PASS / {fail} FAIL")
print("=" * 68)

sys.exit(1 if fail else 0)
