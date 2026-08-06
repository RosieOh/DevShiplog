"""기술 스택 추출과 신선도.

이 두 가지가 제품의 차별점이므로, 여기가 틀리면 나머지가 다 무의미하다.
"""

from datetime import datetime, timedelta

import pytest

from src.domain.services import freshness as fresh
from src.domain.services.freshness import StackRef, evaluate, outdated_stacks
from src.domain.services.tech_stack import detect, normalize

NOW = datetime(2026, 8, 6)


# ------------------------------------------------------------------ 정규화


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("React", "react"), ("react.js", "react"), ("reactjs", "react"), ("리액트", "react"),
        ("Next.js", "nextjs"), ("next", "nextjs"),
        ("py", "python"), ("Python3", "python"),
        ("postgres", "postgresql"), ("psql", "postgresql"),
        ("k8s", "kubernetes"),
        ("@types/react", "react"),  # npm 스코프는 벗긴다
    ],
)
def test_표기가_달라도_하나의_이름으로(raw, expected):
    """자유 문자열로 두면 "React 18 글 모음" 질의가 성립하지 않는다."""
    assert normalize(raw) == expected


def test_모르는_이름은_추측하지_않는다():
    """추측해서 틀린 메타데이터를 만드느니 없는 편이 낫다."""
    assert normalize("우리회사내부툴") is None
    assert normalize("") is None


# ------------------------------------------------------------------ 추출


def test_package_json_에서_이름과_버전을_함께():
    md = '```json\n{ "dependencies": { "react": "^18.3.1", "next": "14.2.0" } }\n```'
    found = {s.name: s for s in detect(md)}
    assert found["react"].version == "18.3"
    assert found["react"].confidence == "high"
    assert found["nextjs"].version == "14.2"


def test_패치_버전은_버린다():
    """18.3.1 과 18.3.2 는 글의 유효성 관점에서 같다."""
    md = '```json\n{ "dependencies": { "react": "18.3.7" } }\n```'
    assert detect(md)[0].version == "18.3"


def test_requirements_에서():
    md = "```\nfastapi==0.115.6\ndjango>=5.0\n```"
    found = {s.name: s.version for s in detect(md)}
    assert found["fastapi"] == "0.115"
    assert found["django"] == "5.0"


def test_코드_펜스_언어는_확실한_신호():
    found = {s.name: s.confidence for s in detect("```python\nprint(1)\n```")}
    assert found["python"] == "high"


def test_tsx_는_react_로():
    assert "react" in {s.name for s in detect("```tsx\nconst a = 1\n```")}


def test_import_는_버전_없이_medium():
    md = "```js\nimport { createClient } from 'redis'\n```"
    found = {s.name: s for s in detect(md)}
    assert found["redis"].version is None
    assert found["redis"].confidence == "medium"


def test_본문의_React_18_표현():
    found = {s.name: s.version for s in detect("React 18 에서 겪은 문제입니다.")}
    assert found["react"] == "18"


def test_코드_안의_숫자를_버전으로_오인하지_않는다():
    """`timeout = 30` 을 "timeout 30" 으로 읽으면 안 된다."""
    md = "```python\ntimeout = 30\nredis = 7\n```"
    versions = {s.name: s.version for s in detect(md)}
    assert versions.get("redis") is None


def test_버전_있는_쪽을_남긴다():
    """import 로도 나오고 package.json 으로도 나오면 버전이 있는 쪽이 쓸모 있다."""
    md = (
        "```js\nimport React from 'react'\n```\n"
        '```json\n{ "dependencies": { "react": "18.3.0" } }\n```'
    )
    assert {s.name: s.version for s in detect(md)}["react"] == "18.3"


def test_빈_본문():
    assert detect("") == []


def test_개수_상한():
    """스택이 20개 붙은 글은 스택 정보가 없는 것과 같다."""
    md = "\n".join(f"```{lang}\nx\n```" for lang in
                   ["python", "js", "ts", "go", "rust", "java", "kotlin", "swift",
                    "ruby", "php", "sql", "bash", "dockerfile"])
    assert len(detect(md)) <= 12


# ------------------------------------------------------------------ 신선도


def test_검증이_최근이면_fresh():
    result = evaluate(NOW - timedelta(days=10), NOW - timedelta(days=800), [], now=NOW)
    assert result.level == fresh.FRESH
    # 2년 전에 쓴 글이어도 최근에 확인했으면 믿을 수 있다.


def test_검증이_오래되면_단계가_내려간다():
    assert evaluate(NOW - timedelta(days=300), None, [], now=NOW).level == fresh.AGING
    assert evaluate(NOW - timedelta(days=700), None, [], now=NOW).level == fresh.STALE


def test_검증한_적_없으면_unverified():
    result = evaluate(None, NOW - timedelta(days=30), [], now=NOW)
    assert result.level == fresh.UNVERIFIED
    # "확인한 적 없음" 과 "확인했는데 오래됨" 은 독자에게 다른 정보다.
    assert result.days_since_verified == 30


def test_검증_없이_아주_오래되면_stale():
    assert evaluate(None, NOW - timedelta(days=900), [], now=NOW).level == fresh.STALE


def test_메이저가_뒤처지면_최근_검증도_한_단계_내려간다():
    """"어제 확인함" 이 "React 17 기준" 을 덮지는 못한다."""
    result = evaluate(NOW - timedelta(days=1), None, [StackRef("react", "17")], now=NOW)
    assert result.level == fresh.AGING
    assert result.outdated[0]["latest_major"] == 19


def test_최신_메이저면_그대로_fresh():
    result = evaluate(NOW - timedelta(days=1), None, [StackRef("react", "19")], now=NOW)
    assert result.level == fresh.FRESH
    assert result.outdated == []


def test_마이너_차이는_세지_않는다():
    """18.2 → 18.3 때문에 경고를 띄우면 경고가 흔해져 아무도 안 본다."""
    assert outdated_stacks([StackRef("react", "19.0")]) == []


def test_모르는_스택은_판정하지_않는다():
    assert outdated_stacks([StackRef("우리회사툴", "3")]) == []


def test_버전이_없으면_판정하지_않는다():
    assert outdated_stacks([StackRef("react", None)]) == []


def test_이유는_화면에_그대로_쓸_수_있어야_한다():
    result = evaluate(NOW - timedelta(days=1), None, [StackRef("react", "17")], now=NOW)
    assert "react 17" in result.reason
    assert result.reason.endswith("다.")


def test_아무_정보도_없으면():
    result = evaluate(None, None, [], now=NOW)
    assert result.level == fresh.UNVERIFIED
    assert result.days_since_verified is None
