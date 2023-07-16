# How to contribute

Thank you for wanting to give this project a hand. It's really appreciated.

This project is developped with `Python`.
To get your development  environment started, here are a few tips.

Have [poetry](https://python-poetry.org/docs/#installation) installed.

Fork, then clone the repo:

```shell
git clone git@github.com:your-username/dramatiq-azure.git
```

Set up your machine:

```
cd path/to/the/code
poetry install --with dev
```

Set-up pre-commit rules
```
poetry run pre-commit install
```

Make sure the tests pass:

```shell
poetry run pytest
```

Use [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) for your commits to help automate the change log. You can also use the `cz` command from [commitizen](https://commitizen-tools.github.io/commitizen/) (in the dev dependencies) to help you write better commit messages - although I'll admit it can get cumbersome.

```shell
poetry run cz commit
```
Make your change. Add tests for your change. Make the tests pass.
Your tests should follow the [Arrange, Act and Assert](https://jamescooke.info/arrange-act-assert-pattern-for-python-developers.html) pattern as much as possible.

```
poetry run pytest
```

Make sure you lint and format the code as well (should be automatic if you installed the `pre-commit` rules)
```shell
poetry run flake8 --max-complexity 10 .
poetry run black .
poetry run isort --ac -l 80 -m 3 --fgw 2 --fass --ca --profile=black .
```

All green? You're ready to submit a [pull request](https://github.com/bidossessi/dramatiq-azure/compare).
Let us know:
- what the issue was (link to an existing issue?)
- a short description of how you solve it

And you're done!

As soon as possible, your changes will be reviewed for inclusion into the codebase if all goes well, with our thanks.

**Working on your first Pull Request?** You can learn how from this *free* series [How to Contribute to an Open Source Project on GitHub](https://kcd.im/pull-request)
