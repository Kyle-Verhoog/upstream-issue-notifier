import os

from github import Github


GH_TOKEN = os.getenv("GITHUB_TOKEN")
GH_REPO = os.getenv("GITHUB_REPOSITORY")
LABELS = os.getenv("LABELS")
LABELS = list(LABELS.split(",")) if LABELS else []


gh = Github(GH_TOKEN)
repo = gh.get_repo(GH_REPO)
repo.create_issue(
    title="Testing 1 2 3",
    body="test test test",
    labels=LABELS,
)
