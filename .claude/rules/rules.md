# 작업 규칙

## 중요: GitHub 작업은 반드시 `github/` 봇 스크립트를 사용할 것

이 레포에서 이슈 생성, 브랜치 생성, PR 생성, 리뷰 요청 등 **모든 GitHub 작업**은
`github/` 모듈을 통해 수행해야 한다.

- `gh` CLI, 직접 `git push` 후 수동 PR 생성 등은 사용하지 않는다.
- 작업 전 `github_bot.json`이 올바르게 설정되어 있어야 한다.

### github_bot.json 설정 (최초 1회)

```json
{
  "app_id": <GitHub App ID>,
  "installation_id": <Installation ID>,
  "private_key_path": "<private key .pem 파일 절대 경로>"
}
```

> `owner`/`repo`는 `git remote origin` URL에서 자동으로 감지하므로 적지 않는다.
> `claude-setup`의 `deploy.py`로 배포하면 `github_bot.json`이 자동으로 함께 복사된다.
> `github_bot.json`은 `.gitignore`에 추가해 커밋하지 않는다.

### 봇 사용 방법

```bash
# 이슈 생성
python github/create_issue.py --title "제목" --body "내용"

# 이슈/PR 코멘트 (여러 줄은 --body-file 권장)
python github/comment_issue.py --issue N --body "내용"
python github/comment_issue.py --issue N --body-file plan.md

# 브랜치 생성
python github/create_branch.py --branch feature-#N

# PR 생성
python github/create_pr.py --title "feat(#N): description" --head feature-#N --body "Closes #N\n\n내용"

# 리뷰 요청
python github/request_review.py --pr N --reviewers username

# PR 머지 (머지 후 원격 브랜치 삭제)
python github/merge_pr.py --pr N --delete-branch
python github/merge_pr.py --pr N --method squash --delete-branch

# PR 닫기 (머지하지 않음, 원격 브랜치 삭제)
python github/close_pr.py --pr N --comment "닫는 이유" --delete-branch

# 이슈 닫기 (사유: completed | not_planned)
python github/close_issue.py --issue N --reason not_planned --comment "닫는 이유"

# 원격 브랜치 삭제 (main/master는 보호)
python github/delete_branch.py --branch feature-#N
```

---

## 워크플로우

작업 시작 전 반드시 아래 순서를 따른다.

1. `main` 브랜치에서 최신 코드 pull
2. 이슈 생성 — `github/create_issue.py` 사용, 제목·본문 **한글**
3. 브랜치 생성 — `github/create_branch.py` 사용 (`feature-#N`)
4. 로컬에서 브랜치 체크아웃
5. 이슈에 개발 계획 코멘트 작성 — `github/comment_issue.py` 사용, **한글**
6. 개발
7. PR 생성 — `github/create_pr.py` 사용
8. 리뷰 요청 — `github/request_review.py` 사용
9. **사용자 승인 후** 머지 — `github/merge_pr.py --pr N --delete-branch` 사용

### 중요: 머지는 반드시 사용자 승인 후에만

- PR 생성·리뷰 요청까지 마쳤으면 멈추고, PR 번호를 밝혀 머지 여부를 사용자에게 묻는다.
- 승인은 **PR마다 개별로** 받는다. 이전 PR의 승인은 다음 PR에 적용되지 않는다.
- 개발 계획에 머지가 포함돼 있어도 승인 없이 머지하지 않는다.

### 머지하지 않고 정리할 때

테스트용 작업 등 머지하지 않기로 한 경우:

1. `github/close_pr.py --pr N --comment "..." --delete-branch`
2. `github/close_issue.py --issue N --reason not_planned --comment "..."`
3. 로컬에서 `main` 체크아웃 후 로컬 브랜치 삭제

---

## Git 컨벤션

### 브랜치
```
feature-#<이슈번호>
```

### 커밋 메시지 (영어)
```
type(#N): description
```

| 타입 | 용도 |
|------|------|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `refactor` | 리팩토링 |
| `docs` | 문서 |
| `chore` | 설정·정리 |

규칙: 소문자, 마침표 없음, 이슈 번호 필수

### PR
- 제목: **영어** — `type(#N): description`
- 본문: **한글**, 첫 줄에 `Closes #N` 포함
- base: `main`

---

## 예시

```
이슈:    #5 로그인 기능 구현
브랜치:  feature-#5
커밋:    feat(#5): add login API
PR 제목: feat(#5): add login API
PR 본문: Closes #5
         로그인 API 및 세션 처리 구현
```
