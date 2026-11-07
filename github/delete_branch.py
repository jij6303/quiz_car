"""
원격 브랜치 삭제 스크립트

단독 실행:
    python delete_branch.py --branch feature-#1

모듈 사용:
    from github.delete_branch import delete_branch
    delete_branch(token, owner, repo, branch_name)
"""
import argparse
from urllib.parse import quote

import requests

from auth import get_owner_repo, get_token, make_headers

PROTECTED_BRANCHES = {"main", "master"}


def delete_branch(token, owner, repo, branch_name):
    if branch_name in PROTECTED_BRANCHES:
        raise SystemExit(f"보호된 브랜치는 삭제할 수 없습니다: {branch_name}")

    ref = quote(branch_name, safe="")
    res = requests.delete(
        f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{ref}",
        headers=make_headers(token),
    )
    if res.status_code == 422:
        raise SystemExit(f"브랜치가 존재하지 않습니다: {branch_name}")
    res.raise_for_status()
    print(f"브랜치 삭제 완료: {branch_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub 원격 브랜치 삭제")
    parser.add_argument("--branch", required=True, help="삭제할 브랜치 이름")
    args = parser.parse_args()

    owner, repo = get_owner_repo()
    token = get_token()
    delete_branch(token, owner, repo, args.branch)
