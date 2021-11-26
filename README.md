# dramatiq-azure
[![CI](https://github.com/bidossessi/dramatiq-azure/actions/workflows/ci.yml/badge.svg)](https://github.com/bidossessi/dramatiq-azure/actions/workflows/ci.yml)
[![Upload Python Package](https://github.com/bidossessi/dramatiq-azure/actions/workflows/python-publish.yml/badge.svg)](https://github.com/bidossessi/dramatiq-azure/actions/workflows/python-publish.yml)

A [Dramatiq](https://dramatiq.io) broker that can be used with [Microsoft Azure](https://azure.microsoft.com/en-us/) queue services.

Heavily inspired by [Dramatiq SQS](https://github.com/Bogdanp/dramatiq_sqs), this package currently implements a broker for [Azure Storage Queue](https://docs.microsoft.com/en-us/azure/storage/queues/). 
An implementation for [Azure Service Bus](https://docs.microsoft.com/en-us/azure/service-bus-messaging/) is planned... eventually.


## Installation

    pip install dramatiq-azure


## Usage


### ASQBroker

The broker looks for `AZURE_STORAGE_CONNECTION_STR` in the environment, to authenticate on Azure Storage.
You need to make sure that the variable exists at runtime.

Creating a connection string for your Azure account is documented [here](https://docs.microsoft.com/en-us/azure/storage/common/storage-configure-connection-string).


``` python
import os
import dramatiq

from dramatiq.middleware import AgeLimit, TimeLimit, Callbacks, Pipelines, Prometheus, Retries
from dramatiq_azure import asqBroker


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

## Tests
Tests require a running [Azurite](https://github.com/Azure/Azurite) instance. You can easily launch `azurite` through [Docker](https://www.docker.com/).

```bash
docker run -p 10000:10000 -p 10001:10001 -p 10002:10002 mcr.microsoft.com/azure-storage/azurite
```