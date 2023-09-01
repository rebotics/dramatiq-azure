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

```shell
cd path/to/the/code
poetry install --with dev
```

Set-up pre-commit rules to automate styling and linting:

```shell
poetry run pre-commit install
```

Make sure the tests pass first (you will need [azurite](https://github.com/Azure/Azurite) running for this):

```shell
poetry run pytest
```

Make your change. Add tests for your change. Make the tests pass.
Your tests should follow the [Arrange, Act and Assert](https://jamescooke.info/arrange-act-assert-pattern-for-python-developers.html) pattern as much as possible.

```shell
poetry run pytest
```

Make sure you lint and format the code as well (should be automatic if you installed the `pre-commit` rules):

```shell
poetry run flake8 --max-complexity 10 .
poetry run black .
poetry run isort --ac -l 80 -m 3 --fgw 2 --fass --ca --profile=black .
```

All green? Time to commit!

> **Warning**
> Use [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) for
your commits; This is required to automate the change log. You can also use the `cz` command from [commitizen](https://commitizen-tools.github.io/commitizen/) (in the dev dependencies) to help you write better commit messages.


```shell
poetry run cz commit
```

You're now ready to submit a [pull request](https://github.com/bidossessi/dramatiq-azure/compare).
Please remember to add a description that explains:
- what problem you are solving (link to any existing github issue)
- a short description of how you solve it

And you're done!

As soon as possible, your changes will be reviewed for inclusion into the codebase if all goes well, with our thanks.

**Working on your first Pull Request?** You can learn how from this *free* series [How to Contribute to an Open Source Project on GitHub](https://kcd.im/pull-request)
