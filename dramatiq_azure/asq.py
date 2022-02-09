from collections import deque
from typing import Iterable, List, Optional
import time
import os
import dramatiq
from azure.core.exceptions import (
    ResourceExistsError,
    HttpResponseError,
)
from azure.storage.queue import (
    QueueClient,
    BinaryBase64EncodePolicy,
    BinaryBase64DecodePolicy,
    QueueMessage,
)


import logging

from dramatiq.common import compute_backoff

# Set the logging level for all azure-storage-* libraries
logger = logging.getLogger("azure")
logger.setLevel(logging.WARNING)

#: The max number of messages that may be prefetched at a time.
MAX_PREFETCH = 32


#: The minimum time to wait between polls in second.
MIN_TIMEOUT = int(os.getenv("DRAMATIQ_ASQ_MIN_TIMEOUT", "20"))

#: to the dead-letter queue (if enabled).
MAX_RECEIVES = 3

#: Azure Storage authentication
CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STR")


def _get_client(queue_name) -> QueueClient:
    return QueueClient.from_connection_string(
        conn_str=CONN_STR,
        queue_name=queue_name,
        message_encode_policy=BinaryBase64EncodePolicy(),
        message_decode_policy=BinaryBase64DecodePolicy(),
    )


def _get_dlq_client(queue_name) -> QueueClient:
    dlqueue_name = f"{queue_name}-dlq"
    return _get_client(dlqueue_name)


class _ASQMessage(dramatiq.MessageProxy):
    def __init__(self, asq_message: QueueMessage, message: dramatiq.Message) -> None:
        super().__init__(message)
        # force type hint
        self.message_id = message.message_id
        self._message = message
        self._asq_message = asq_message

    @classmethod
    def from_queue_message(cls, _message: QueueMessage):
        dramatiq_message = dramatiq.Message.decode(_message.content)
        return cls(_message, dramatiq_message)


class _ASQConsumer(dramatiq.Consumer):
    def __init__(
        self,
        broker,
        queue_name: str,
        prefetch: int,
        timeout: int,
        dead_letter: bool = False,
    ) -> None:
        self.prefetch = min(prefetch, MAX_PREFETCH)
        self.timeout = timeout
        self.visibility_timeout = int(timeout / 1000)
        self.queue_name = queue_name
        self.dead_letter = dead_letter
        self.q_client = _get_client(queue_name)
        self.dlq_client = _get_dlq_client(queue_name) if dead_letter else None

        # local cache
        self.message_cache: List[_ASQMessage] = []
        self.queued_message_ids = set()
        self.misses = 0

    @property
    def outstanding_message_count(self):
        return len(self.queued_message_ids) + len(self.message_cache)

    @property
    def ref_count(self):
        return len(self.messages)

    def ack(self, message: _ASQMessage) -> None:
        self.q_client.delete_message(message._asq_message)
        if message.message_id in self.queued_message_ids:
            self.queued_message_ids.remove(message.message_id)

    def nack(self, message: _ASQMessage) -> None:
        if self.dlq_client:
            self.dlq_client.send_message(message._message.encode())
        self.q_client.delete_message(message._asq_message)
        if message.message_id in self.queued_message_ids:
            self.queued_message_ids.remove(message.message_id)

    def requeue(self, messages: Iterable[_ASQMessage]) -> None:
        # No batch processing
        for message in messages:
            self.q_client.send_message(message._message.encode())
            self.q_client.delete_message(message._asq_message)
            if message.message_id in self.queued_message_ids:
                self.queued_message_ids.remove(message.message_id)

    def __next__(self) -> Optional[_ASQMessage]:
        while True:
            try:
                match = self.message_cache.pop(0)
                self.misses = 0
                self.queued_message_ids.add(match.message_id)
                return match
            except IndexError:
                msg_batch = []
                if self.outstanding_message_count < self.prefetch:
                    fillout = self.prefetch - self.outstanding_message_count
                    pager = self.q_client.receive_messages(
                        messages_per_page=fillout,
                        visibility_timeout=self.visibility_timeout,
                    )
                    msg_batch = [item for item in next(pager.by_page())]
                    self.message_cache = [_ASQMessage.from_queue_message(_msg) for _msg in msg_batch]
                if not msg_batch:
                    self.misses, backoff_ms = compute_backoff(self.misses, max_backoff=self.timeout)
                    time.sleep(backoff_ms)
                    return None


class ASQBroker(dramatiq.Broker):
    """A Dramatiq_ broker that can be used with `Azure Storage Queues`_
    This backend has a number of limitations compared to the built-in
    Redis and RMQ backends:
      * messages can be at most 64KiB large,
    The backend uses the `Python Azure SDK`_ (v12).
    Parameters:
      middleware: The set of middleware that apply to this broker.
      dead_letter: Whether to add a dead-letter queue. Defaults to false.
    .. _Dramatiq: https://dramatiq.io
    .. _Azure Storage Queues: https://docs.microsoft.com/en-us/azure/storage/queues/
    .. _Python Azure SDK: http://boto3.readthedocs.io/en/latest/index.html
    """

    def __init__(
        self,
        *,
        dead_letter: bool = False,
        middleware=None,
    ) -> None:
        super().__init__(middleware=middleware)
        self.queues: set = set()
        self.dead_letter = dead_letter

    def consume(self, queue_name: str, prefetch: int = 1, timeout: int = 5000) -> dramatiq.Consumer:
        if queue_name not in self.queues:
            raise dramatiq.errors.QueueNotFound(queue_name)
        return _ASQConsumer(self, queue_name, prefetch, timeout, dead_letter=self.dead_letter)

    def declare_queue(self, queue_name: str) -> None:

        if queue_name not in self.queues:
            self.emit_before("declare_queue", queue_name)
            try:
                q_client = _get_client(queue_name)
                q_client.create_queue()
                if self.dead_letter:
                    dlq_client = _get_dlq_client(queue_name)
                    dlq_client.create_queue()
            except ResourceExistsError:
                pass
            self.queues.add(queue_name)
            self.emit_after("declare_queue", queue_name)

    def enqueue(self, message: dramatiq.Message, *, delay: Optional[int] = None) -> dramatiq.Message:
        queue_name = message.queue_name
        if queue_name not in self.queues:
            raise dramatiq.errors.QueueNotFound(queue_name)

        delay_sec = int(delay / 1000) if delay else 0

        logger.debug(f"Enqueueing message {message.message_id} on queue {queue_name}.")
        self.emit_before("enqueue", message, delay)
        q_client = _get_client(queue_name)
        try:
            q_client.send_message(message.encode(), visibility_timeout=delay_sec)
            self.emit_after("enqueue", message, delay)
            return message
        except HttpResponseError as e:
            raise RuntimeError(str(e))

    def flush(self, queue_name: str):
        if queue_name not in self.queues:
            raise dramatiq.errors.QueueNotFound(queue_name)
        q_client = _get_client(queue_name)
        q_client.clear_messages()

    def flush_all(self):
        for queue_name in self.queues:
            self.flush(queue_name)

    def get_declared_queues(self) -> Iterable[str]:
        return self.queues

    def get_declared_delay_queues(self) -> Iterable[str]:
        return set()
