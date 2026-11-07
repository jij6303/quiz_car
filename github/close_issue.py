"""
이슈 닫기 스크립트

단독 실행:
    python close_issue.py --issue 1
    python close_issue.py --issue 1 --reason not_planned --comment "테스트용이라 닫습니다."

모듈 사용:
    from github.close_issue import close_issue
    close_issue(token, owner, repo, issue_number, reason, comment)
"""
import argparse

import requests

from auth import get_owner_repo, get_token, make_headers


def close_issue(token, owner, repo, issue_number, reason="completed", comment=None):
    headers = make_headers(token)
    base_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"

    if comment:
        res = requests.post(f"{base_url}/comments", headers=headers, json={"body": comment})
        res.raise_for_status()

    res = requests.patch(
        base_url,
        headers=headers,
        json={"state": "closed", "state_reason": reason},
    )
    res.raise_for_status()
    issue = res.json()
    print(f"이슈 닫기 완료: #{issue['number']} {issue['title']} ({reason})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub 이슈 닫기")
    parser.add_argument("--issue", required=True, type=int, help="이슈 번호")
    parser.add_argument(
        "--reason",
        default="completed",
        choices=["completed", "not_planned"],
        help="닫는 사유 (기본값: completed)",
    )
    parser.add_argument("--comment", default=None, help="닫기 전에 남길 코멘트")
    args = parser.parse_args()

    owner, repo = get_owner_repo()
    token = get_token()
    close_issue(token, owner, repo, args.issue, args.reason, args.comment)
