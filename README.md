# dramatiq-azure
[![CI](https://github.com/bidossessi/dramatiq-azure/actions/workflows/ci.yml/badge.svg)](https://github.com/bidossessi/dramatiq-azure/actions/workflows/ci.yml)
[![Pypi](https://github.com/bidossessi/dramatiq-azure/actions/workflows/python-publish.yml/badge.svg)](https://github.com/bidossessi/dramatiq-azure/actions/workflows/python-publish.yml)
[![codecov](https://codecov.io/gh/bidossessi/dramatiq-azure/branch/main/graph/badge.svg?token=6LLEDAM3SG)](https://codecov.io/gh/bidossessi/dramatiq-azure)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://makeapullrequest.com)


A [Dramatiq](https://dramatiq.io) broker that can be used with [Microsoft Azure](https://azure.microsoft.com/en-us/) queue services.

Heavily inspired by [Dramatiq SQS](https://github.com/Bogdanp/dramatiq_sqs), this package currently implements a broker for [Azure Storage Queue](https://docs.microsoft.com/en-us/azure/storage/queues/).
An implementation for [Azure Service Bus](https://docs.microsoft.com/en-us/azure/service-bus-messaging/) is planned... eventually.


## Installation

```shell
    pip install dramatiq-azure
    pip install dramatiq-azure[identity]  # for passwordless authentication
```
## Usage

### ASQBroker

```python
import dramatiq

from dramatiq.middleware import AgeLimit, TimeLimit, Callbacks, Pipelines, Prometheus, Retries
from dramatiq_azure import ASQBroker


broker = ASQBroker(
    dead_letter=True,
    middleware=[
        Prometheus(),
        AgeLimit(),
        TimeLimit(),
        Callbacks(),
        Pipelines(),
        Retries(min_backoff=1000, max_backoff=900000, max_retries=96),
    ],
)
dramatiq.set_broker(broker)
```

### Authentication

The following authentication methods are supported by the broker:
1. Connection string based: `AZURE_STORAGE_CONNECTION_STR` environment variable must be set.
If this variable is not set, passwordless authentication will be used.
Creating a connection string for your Azure account is documented [here](https://docs.microsoft.com/en-us/azure/storage/common/storage-configure-connection-string).
2. [Passwordless](https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication-overview#recommended-app-authentication-approach) (token-based) authentication **(Recommended)**: `AZURE_STORAGE_ACCOUNT_NAME` environment variable must be set.

The list of other mandatory variables depends on where the app is being run.
More information can be found [here](https://learn.microsoft.com/en-us/azure/storage/queues/storage-quickstart-queues-python?tabs=passwordless%2Croles-azure-portal%2Cenvironment-variable-windows%2Csign-in-azure-cli#authenticate-to-azure).

### Environment variables

The following environment variables can be used to configure the broker:
- `AZURE_STORAGE_CONNECTION_STR`: Azure Storage connection string;
- `AZURE_STORAGE_ACCOUNT_NAME`/`AZURE_ACCOUNT_NAME`: Azure Storage account name;
- `AZURE_ENDPOINT_SUFFIX`: Azure Storage endpoint suffix;
- `AZURE_SSL`: Whether to use SSL for the connection;
- `AZURE_QUEUE_ACCOUNT_URL`: Azure Storage account URL;
- `DRAMATIQ_ASQ_MIN_TIMEOUT`: The minimum time to wait between polls in second.

## Tests

Tests require a running [Azurite](https://github.com/Azure/Azurite) instance. You can easily launch `azurite` through [Docker](https://www.docker.com/).

```shell
docker run -p 10000:10000 -p 10001:10001 -p 10002:10002 mcr.microsoft.com/azure-storage/azurite
```

Run the test suite

```shell
pytest
```

## Contributions

Found an itch you know how to scratch? PR welcome (just remember to read the
[contribution guide](CONTRIBUTING.md)) !
