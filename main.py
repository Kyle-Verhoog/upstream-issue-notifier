#!/usr/local/bin/python
from collections import defaultdict
import os
import re

import git
from github import Github


GH_TOKEN = os.getenv("GITHUB_TOKEN")
GH_REPO = os.getenv("GITHUB_REPOSITORY")
LABELS = os.getenv("LABELS")
LABELS = list(LABELS.split(",")) if LABELS else []


gh = Github(GH_TOKEN)

upstream_issues = defaultdict(lambda: {
    "issue": None,
    "files": [],
})

# Get all files from git to scan them for issues.
g = git.Git()
for file_name in g.ls_files().split("\n"):
    if not os.path.isfile(file_name):
        continue

    with open(file_name) as file:
        lines = file.readlines()
        lineno = 0
        for line in lines:
            lineno += 1
            match = re.search("(?P<owner>[a-zA-Z0-9-]+)/(?P<repo>[a-zA-Z0-9-]+)/issues/(?P<number>[0-9]+)", line)
            if match:
                owner = match.group("owner")
                repo = match.group("repo")
                issue_no = match.group("number")

                ref = f"{owner}/{repo}#{issue_no}"
                if upstream_issues[ref]["issue"] is None:
                    repo = gh.get_repo("%s/%s" % (owner, repo))
                    issue = repo.get_issue(number=int(issue_no))
                    upstream_issues[ref]["issue"] = issue
                upstream_issues[ref]["files"].append((file_name, lineno))


repo = gh.get_repo(GH_REPO)
repo_ref = os.getenv("GITHUB_REF_NAME")
server_url = os.getenv("GITHUB_SERVER_URL")

# Find issues that have already been reported for the upstream
repo_issues = repo.get_issues()
for ref in upstream_issues.keys():
    upstream_issue = upstream_issues[ref]["issue"]
    if upstream_issue.state == "closed":
        files = upstream_issues[ref]["files"]
        files_str = "\n".join(f"  - [{fn}:{ln}]({server_url}/{GH_REPO}/blob/{repo_ref}/{fn}#L{ln})" for fn, ln in files)
        body = f"""Upstream issue {ref} referenced in the file{'s' if len(files) > 1 else ''}:

{files_str}

has been closed.

The code referencing these issues could potentially be updated.
"""

        # Search for any issue created already for the upstream issue.
        for repo_issue in repo_issues:
            if ref in repo_issue.title:
                # repo issue already exists for the upstream issue
                repo_issue.edit(
                    body=body,
                )
                break
        else:
            # Create the tracking issue
            repo.create_issue(
                title=f"Upstream issue {ref} closed",
                body=body,
                labels=LABELS,
            )

# Blocked on https://github.com/Kyle-Verhoog/upstream-issue-notifier/issues/2
# Blocked on https://github.com/Kyle-Verhoog/upstream-issue-notifier/issues/3
