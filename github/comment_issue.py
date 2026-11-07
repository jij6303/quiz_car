"""
이슈/PR 코멘트 작성 스크립트

단독 실행:
    python comment_issue.py --issue 1 --body "내용"
    python comment_issue.py --issue 1 --body-file plan.md

모듈 사용:
    from github.comment_issue import comment_issue
    comment_url = comment_issue(token, owner, repo, issue_number, body)
"""
import argparse
from pathlib import Path

import requests

from auth import get_owner_repo, get_token, make_headers


def comment_issue(token, owner, repo, issue_number, body):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
    res = requests.post(url, headers=make_headers(token), json={"body": body})
    res.raise_for_status()
    comment = res.json()
    print(f"코멘트 작성 완료: #{issue_number}")
    print(f"URL: {comment['html_url']}")
    return comment["html_url"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub 이슈/PR 코멘트 작성")
    parser.add_argument("--issue", required=True, type=int, help="이슈 또는 PR 번호")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--body", help="코멘트 본문")
    group.add_argument("--body-file", help="코멘트 본문이 담긴 파일 경로 (UTF-8)")
    args = parser.parse_args()

    body = args.body if args.body is not None else Path(args.body_file).read_text(encoding="utf-8")

    owner, repo = get_owner_repo()
    token = get_token()
    comment_issue(token, owner, repo, args.issue, body)
