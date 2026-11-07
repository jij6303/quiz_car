"""
PR 머지 스크립트

단독 실행:
    python merge_pr.py --pr 1
    python merge_pr.py --pr 1 --method squash --delete-branch

모듈 사용:
    from github.merge_pr import merge_pr
    sha = merge_pr(token, owner, repo, pr_number, method, delete_branch)
"""
import argparse
from urllib.parse import quote

import requests

from auth import get_owner_repo, get_token, make_headers


def merge_pr(token, owner, repo, pr_number, method="merge", delete_branch=False):
    headers = make_headers(token)
    base_url = f"https://api.github.com/repos/{owner}/{repo}"

    res = requests.get(f"{base_url}/pulls/{pr_number}", headers=headers)
    res.raise_for_status()
    pr = res.json()
    if pr["merged"]:
        raise SystemExit(f"PR #{pr_number}은(는) 이미 머지되었습니다.")
    if pr["state"] != "open":
        raise SystemExit(f"PR #{pr_number}이(가) 닫혀 있습니다.")

    res = requests.put(
        f"{base_url}/pulls/{pr_number}/merge",
        headers=headers,
        json={"merge_method": method},
    )
    if not res.ok:
        raise SystemExit(f"머지 실패 ({res.status_code}): {res.json().get('message')}")
    sha = res.json()["sha"]
    print(f"머지 완료: PR #{pr_number} {pr['title']} ({method}, sha: {sha[:7]})")

    if delete_branch:
        head = pr["head"]
        if head["repo"] and head["repo"]["full_name"] == f"{owner}/{repo}":
            ref = quote(head["ref"], safe="")
            res = requests.delete(f"{base_url}/git/refs/heads/{ref}", headers=headers)
            res.raise_for_status()
            print(f"브랜치 삭제 완료: {head['ref']}")
        else:
            print("포크 브랜치라 삭제를 건너뜁니다.")

    return sha


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub PR 머지")
    parser.add_argument("--pr", required=True, type=int, help="PR 번호")
    parser.add_argument("--method", default="merge", choices=["merge", "squash", "rebase"], help="머지 방식 (기본값: merge)")
    parser.add_argument("--delete-branch", action="store_true", help="머지 후 head 브랜치 원격 삭제")
    args = parser.parse_args()

    owner, repo = get_owner_repo()
    token = get_token()
    merge_pr(token, owner, repo, args.pr, args.method, args.delete_branch)
