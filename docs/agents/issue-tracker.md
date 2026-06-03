# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues. Use the `gh` CLI for all operations.

## Repository

GitHub repository: `KG9750/TechNews`

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v`; `gh` does this automatically when run inside this clone.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.

## Readiness Gate Check

Before moving MVP issues from `needs-triage` to an implementation-ready label, run:

```bash
python3 scripts/check_readiness.py --require-github
```

This verifies GitHub auth, origin remote identity, default branch, push-capable repo permission, canonical triage labels, `pre-development`/`mvp`/`post-mvp` milestones, pre-development tracking issues, and that MVP issues #10-#20 remain `needs-triage` while the readiness gate is not passed.
