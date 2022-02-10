import os
import random
import string

import pytest
from unittest import mock

import dramatiq
from dramatiq.middleware import AgeLimit, Callbacks, Pipelines, Retries, TimeLimit

from dramatiq_azure import asq


@pytest.fixture
def asq_broker():
    broker = asq.ASQBroker(
        dead_letter=True,
        middleware=[
            AgeLimit(),
            TimeLimit(),
            Callbacks(),
            Pipelines(),
            Retries(min_backoff=1000, max_backoff=900000, max_retries=96),
        ],
    )
    dramatiq.set_broker(broker)
    yield broker
    for queue_name in broker.queues:
        client = asq._get_client(queue_name)
        client.delete_queue()
        if broker.dead_letter:
            dlq_client = asq._get_dlq_client(queue_name)
            dlq_client.delete_queue()


@pytest.fixture
def queue_name():
    letters = string.ascii_lowercase
    result_str = "".join(random.choice(letters) for i in range(7))
    return f"queue{result_str}"


@pytest.fixture
def worker(asq_broker):
    worker = dramatiq.Worker(asq_broker, worker_threads=1)
    worker.start()
    yield worker
    worker.stop()
