#!/usr/local/bin/python
from collections import defaultdict
import logging
import os
import re
from typing import Dict, List, NamedTuple, Set, Tuple

import git
import github
from github.GithubException import UnknownObjectException


GH_TOKEN = os.getenv("GITHUB_TOKEN")
LABELS = os.getenv("LABELS")
LABELS = list(LABELS.split(",")) if LABELS else []
IGNORE_DIRS = os.getenv("IGNORE_DIRS")
IGNORE_DIRS = list(IGNORE_DIRS.split(",") if IGNORE_DIRS else [])
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DRY_RUN = bool(os.getenv("DRY_RUN", False))
logging.basicConfig(level=LOG_LEVEL)

if GH_TOKEN is None:
    logging.warning("not Github token set, likely to hit api limit")




def repo_filenames(repo: git.Git) -> List[str]:
    return repo.ls_files().split("\n")


def filter_filenames(filenames: List[str]) -> List[str]:
    filtered_filenames = []
    for filename in filenames:
        if not os.path.isfile(filename):
            continue
        if any(filename.startswith(ignore) for ignore in IGNORE_DIRS):
            logging.debug("Ignoring file %r due to IGNORE_DIRS", filename)
            continue
        filtered_filenames.append(filename)
    return filtered_filenames


class FileIssue(NamedTuple):
    owner: str
    repo: str
    num: int
    filename: str
    lineno: int

    @property
    def ref(self) -> str:
        return "%s/%s#%d" % (self.owner, self.repo, self.num)

    def __str__(self) -> str:
        return f"%s (%s:%s)" % (self.ref, self.filename, self.lineno)

    def __repr__(self) -> str:
        return repr(str(self))


def find_issues_in_filenames(file_names: List[str]) -> List[FileIssue]:
    upstream_issues = []
    for filename in filenames:
        with open(filename) as file:
            try:
                lines = file.readlines()
            except UnicodeDecodeError:
                # Skip non-utf encoded files
                continue
            lineno = 0
            for line in lines:
                lineno += 1
                match = re.search(
                    "(?P<owner>[a-zA-Z0-9-]+)/(?P<repo>[a-zA-Z0-9-]+)/issues/(?P<number>[0-9]+)",
                    line,
                )
                if match:
                    owner = match.group("owner")
                    repo = match.group("repo")
                    issue_no = match.group("number")

                    upstream_issues.append(
                        FileIssue(
                            owner=owner,
                            repo=repo,
                            num=int(issue_no),
                            filename=filename,
                            lineno=lineno,
                        )
                    )
    return upstream_issues


def issues_by_repo(issues: List[FileIssue]) -> Dict[str, Set[FileIssue]]:
    repos: Dict[str, Set[FileIssue]] = defaultdict(lambda: set())
    for issue in issues:
        repos["%s/%s" % (issue.owner, issue.repo)].add(issue)
    return repos


def get_closed_issues(
    issues: List[FileIssue], gh: github.Github
) -> List[Tuple[FileIssue, github.Issue.Issue]]:
    closed_issues = []
    for repo, issues in issues_by_repo(issues).items():
        try:
            gh_repo = gh.get_repo(repo)
        except UnknownObjectException:
            logging.error("failed to look up issue %r", issue.ref)
        else:
            for issue in issues:
                try:
                    gh_issue = gh_repo.get_issue(number=issue.num)
                except github.GithubException.UnknownObjectException:
                    logging.error("failed to look up issue %r", issue.ref)
                else:
                    if gh_issue.state == "closed" and gh_issue not in [ghi[1] for ghi in closed_issues]:
                        closed_issues.append((issue, gh_issue))
    return closed_issues


def get_unique_issues(
    issues: List[FileIssue]
) -> Dict[str, List[FileIssue]]:
    """Return issues without duplicates based on ref"""
    dedupe_issues = {}
    for issue in issues:
        for ref in dedupe_issues:
            if ref == issue.ref:
                dedupe_issues[ref].append(issue)
                break
        else:
            dedupe_issues[issue.ref] = [issue]
    return dedupe_issues


def get_issue_locations(
    issues: Dict[str, List[FileIssue]], closed_issue: FileIssue
) -> List[Tuple[str, int]]:
    """Return all the name and line number of all the files that contain the issue"""
    locations = []
    for ref, issues in unique_issues.items():
        for issue in issues:
            if issue.ref == closed_issue.ref:
                locations.append((issue.filename, issue.lineno))
    return locations


if __name__ == "__main__":
    g = git.Git()
    all_filenames = repo_filenames(g)
    filenames = filter_filenames(repo_filenames(g))
    logging.info("filtered %r files", len(all_filenames) - len(filenames))
    issues = find_issues_in_filenames(filenames)
    logging.info("found %r issues in %r files", len(issues), len(filenames))

    gh = github.Github(os.getenv("GITHUB_TOKEN"))
    closed_issues = get_closed_issues(issues, gh)
    logging.info("found %r closed issues", len(closed_issues))

    GH_REPO = os.getenv("GITHUB_REPOSITORY")
    gh_repo = gh.get_repo(GH_REPO)
    repo_ref = os.getenv("GITHUB_REF_NAME")
    server_url = os.getenv("GITHUB_SERVER_URL")

    repo_issues = gh_repo.get_issues()
    unique_issues = get_unique_issues(issues)
    for (issue, gh_issue) in closed_issues:
        locations = get_issue_locations(unique_issues, issue)

        
        files_str = "\n".join(
            f"  - [{fn}:{ln}]({server_url}/{GH_REPO}/blob/{repo_ref}/{fn}#L{ln})"
            for fn, ln in locations
        )
        body = f"""Upstream issue {issue.ref} referenced in the file{'s' if len(locations) > 1 else ''}:

{files_str}

has been closed.

The code referencing this issue could potentially be updated.
    """
        for repo_issue in repo_issues:
            if not DRY_RUN:
                if issue.ref in repo_issue.title or issue.ref in repo_issue.body:
                    # repo issue already exists for the upstream issue, update it
                    # in case any references have been removed.
                    repo_issue.edit(
                        body=body,
                    )
                    break
            else:
                logging.info(f"Would edit issue number {repo_issue.number} in repo `{GH_REPO}`:\nUpstream issue {issue.ref}\n\n{body}"),

        else:
            if not DRY_RUN:
                gh_repo.create_issue(
                    title=f"Upstream issue {issue.ref} closed",
                    body=body,
                    labels=LABELS,
                )
            else:
                logging.info(f"Would create issue in repo '{GH_REPO}':\nUpstream issue {issue.ref}\n\n{body}"),
