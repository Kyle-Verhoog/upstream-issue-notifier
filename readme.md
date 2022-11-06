# upstream issue notifier

Automatically create Github issues in a repository when references to upstream
issues in other repositories are closed.


## usage

```yaml
# .github/workflows/upstream-issue-notifier

name: Upstream issue notifier
on:
  push:
    branches:
      - master
jobs:
  upstream-issues:
    runs-on: ubuntu-latest
    steps:
      - name: upstream-issue-notifier
        uses: Kyle-Verhoog/upstream-issue-notifier@v0.0.4
```


## useful links

- https://docs.github.com/en/actions/learn-github-actions/environment-variables
- https://gitpython.readthedocs.io/en/stable/index.html
- https://pygithub.readthedocs.io/en/latest/
