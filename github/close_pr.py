"""
PR 닫기 스크립트 (머지하지 않음)

단독 실행:
    python close_pr.py --pr 1
    python close_pr.py --pr 1 --comment "테스트용이라 닫습니다." --delete-branch

모듈 사용:
    from github.close_pr import close_pr
    close_pr(token, owner, repo, pr_number, comment, delete_branch)
"""
import argparse

import requests

from auth import get_owner_repo, get_token, make_headers
from delete_branch import delete_branch as delete_remote_branch


def close_pr(token, owner, repo, pr_number, comment=None, delete_branch=False):
    headers = make_headers(token)
    base_url = f"https://api.github.com/repos/{owner}/{repo}"

    res = requests.get(f"{base_url}/pulls/{pr_number}", headers=headers)
    res.raise_for_status()
    pr = res.json()
    if pr["merged"]:
        raise SystemExit(f"PR #{pr_number}은(는) 이미 머지되었습니다.")

    if pr["state"] == "open":
        if comment:
            res = requests.post(
                f"{base_url}/issues/{pr_number}/comments",
                headers=headers,
                json={"body": comment},
            )
            res.raise_for_status()
        res = requests.patch(
            f"{base_url}/pulls/{pr_number}",
            headers=headers,
            json={"state": "closed"},
        )
        res.raise_for_status()
        print(f"PR 닫기 완료: #{pr_number} {pr['title']}")
    else:
        print(f"PR #{pr_number}은(는) 이미 닫혀 있습니다.")

    if delete_branch:
        head = pr["head"]
        if head["repo"] and head["repo"]["full_name"] == f"{owner}/{repo}":
            delete_remote_branch(token, owner, repo, head["ref"])
        else:
            print("포크 브랜치라 삭제를 건너뜁니다.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub PR 닫기 (머지하지 않음)")
    parser.add_argument("--pr", required=True, type=int, help="PR 번호")
    parser.add_argument("--comment", default=None, help="닫기 전에 남길 코멘트")
    parser.add_argument("--delete-branch", action="store_true", help="닫은 뒤 head 브랜치 원격 삭제")
    args = parser.parse_args()

    owner, repo = get_owner_repo()
    token = get_token()
    close_pr(token, owner, repo, args.pr, args.comment, args.delete_branch)
