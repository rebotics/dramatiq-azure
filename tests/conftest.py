import logging
import random
import uuid
import os

import pytest
from unittest import mock

import dramatiq
from dramatiq.middleware import (
    AgeLimit, 
    Callbacks, 
    Pipelines, 
    Retries,
    TimeLimit
)

from dramatiq_azure import asq

logfmt = "[%(asctime)s] [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.DEBUG, format=logfmt)
logging.getLogger("botocore").setLevel(logging.WARN)
random.seed(1337)



@pytest.fixture(autouse=True)
def set_env_vars():
    os.environ[asq.CONN_ENV] = """
DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;
AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;
BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;
QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;
TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;
"""

@pytest.fixture
def asq_broker():
    broker = asq.ASQBroker(
        namespace="dramatiq_azure_tests",
        middleware=[
            AgeLimit(),
            TimeLimit(),
            Callbacks(),
            Pipelines(),
            Retries(min_backoff=1000, max_backoff=900000, max_retries=96),
        ],
        tags={
            "owner": "dramatiq_azure_tests",
        },
    )
    dramatiq.set_broker(broker)
    yield broker
    for queue in broker.queues.values():
        queue.delete()


@pytest.fixture
def queue_name(broker):
    return f"queue_{uuid.uuid4()}"


@pytest.fixture
def worker(broker):
    worker = dramatiq.Worker(broker)
    worker.start()
    yield worker
    worker.stop()