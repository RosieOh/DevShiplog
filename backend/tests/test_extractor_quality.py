"""추출기 품질 회귀 방어.

추출기는 조용히 나빠지기 쉽다. 별칭을 하나 고치거나 정규식을 손대면
다른 형태가 안 잡히는데, 단위 테스트는 그걸 못 잡는다.

그래서 실제 글 모양의 코퍼스에 대고 재현율을 측정하고 **하한을 못 박는다.**
이 수치가 곧 "제품이 동작하는 비율" 이다 — 버전을 못 뽑으면 낡음 판정을 못 하고,
낡음 판정을 못 하면 이 제품은 그냥 블로그다.
"""

import pytest

from src.domain.services.tech_stack import detect
from tests.fixtures.posts_corpus import CORPUS

# 하한.
#
# 지금 코퍼스에서는 100% 지만 하한을 100% 로 잡지 않는다.
# 그러면 어려운 표본을 하나 추가하는 순간 빨간불이 되고, 사람들은 표본을
# 추가하지 않게 된다. 코퍼스가 커지는 것이 하한을 지키는 것보다 중요하다.
#
# 떨어뜨릴 때는 "왜 이 형태는 못 잡아도 되는가" 를 커밋 메시지에 남긴다.
MIN_NAME_RECALL = 0.95
MIN_VERSION_RECALL = 0.90
MAX_FALSE_POSITIVE_RATE = 0.05


def measure():
    hit_name = hit_version = false_positive = total_found = 0
    need_name = need_version = 0
    gaps = []

    for sample in CORPUS:
        found = {s.name: s.version for s in detect(sample["body"])}
        total_found += len(found)

        for name, version in sample["expect"].items():
            need_name += 1
            if version is not None:
                need_version += 1

            if name not in found:
                gaps.append(f"{sample['name']}: {name} 못 찾음")
                continue

            hit_name += 1
            if version is not None:
                if found[name] == version:
                    hit_version += 1
                else:
                    gaps.append(f"{sample['name']}: {name} {version} → {found[name]}")

        for name in found:
            if name not in sample["expect"]:
                false_positive += 1
                gaps.append(f"{sample['name']}: {name} 오탐")

    return {
        "name_recall": hit_name / max(need_name, 1),
        "version_recall": hit_version / max(need_version, 1),
        "false_positive_rate": false_positive / max(total_found, 1),
        "gaps": gaps,
    }


def test_이름_재현율():
    result = measure()
    assert result["name_recall"] >= MIN_NAME_RECALL, (
        f"{result['name_recall']:.0%} < {MIN_NAME_RECALL:.0%}\n" + "\n".join(result["gaps"])
    )


def test_버전_재현율():
    """버전을 못 뽑으면 낡음 판정을 못 한다 — 제품의 핵심이 죽는다."""
    result = measure()
    assert result["version_recall"] >= MIN_VERSION_RECALL, (
        f"{result['version_recall']:.0%} < {MIN_VERSION_RECALL:.0%}\n" + "\n".join(result["gaps"])
    )


def test_오탐률():
    """틀린 메타데이터는 없는 것보다 나쁘다. 독자가 잘못된 근거로 글을 믿는다."""
    result = measure()
    assert result["false_positive_rate"] <= MAX_FALSE_POSITIVE_RATE, (
        f"{result['false_positive_rate']:.0%} > {MAX_FALSE_POSITIVE_RATE:.0%}\n"
        + "\n".join(result["gaps"])
    )


@pytest.mark.parametrize("sample", CORPUS, ids=lambda s: s["name"])
def test_글마다_기대한_이름은_모두_찾는다(sample):
    """어느 글 형태에서 무너졌는지 바로 보이게 한다."""
    found = {s.name for s in detect(sample["body"])}
    missing = set(sample["expect"]) - found
    assert not missing, f"못 찾음: {missing}"
