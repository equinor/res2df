# Contributing

The following is a set of guidelines for contributing to `res2df`.

There are several important ways you can help; here are some examples:

- Submitting bug reports and feature requests: see [Issues](https://github.com/equinor/res2df/issues).
- Proposing code for bug fixes and new features, then [making a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests).
- Fixing typos and generally improving the documentation.
- Writing tutorials, examples, and how-to documents.


## Commits

We strive to keep a consistent and clean git history and all contributions should adhere to the following:

1. All tests should pass on all commits
1. A commit should do one atomic change on the repository
1. The commit headline should be descriptive and in the imperative

Please note that we use [`black`](https://black.readthedocs.io/en/stable/) and [`isort`](https://pycqa.github.io/isort/) for code formatting.


## Pull request process

1. Work on your own fork of the main repo.
1. Push your commits and make a draft pull request using the pull request template.
1. Check that your pull request passes all tests.
1. When all tests have passed and your are happy with your changes, change your pull request to "ready for review", and ask for a code review.
1. When your code has been approved you should rebase, squash and merge your changes.
