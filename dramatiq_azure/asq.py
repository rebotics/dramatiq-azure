from collections import deque
from typing import Iterable, Optional
import time
import os
import dramatiq
from azure.core.exceptions import ResourceExistsError
from azure.storage.queue import (
    QueueClient, 
    BinaryBase64EncodePolicy, 
    BinaryBase64DecodePolicy, 
    QueueMessage,
)


import logging

# Set the logging level for all azure-storage-* libraries
logger = logging.getLogger("azure")
logger.setLevel(logging.WARNING)

#: The max number of messages that may be prefetched at a time.
MAX_PREFETCH = 32


#: The minimum time to wait between polls in second.
MIN_TIMEOUT = int(os.getenv("DRAMATIQ_asq_MIN_TIMEOUT", "20"))

#: The number of times a message will be received before being added
#: to the dead-letter queue (if enabled).
MAX_RECEIVES = 3

CONN_ENV  = "AZURE_STORAGE_CONNECTION_STR"

#: The Azure Storage connection string
CONN_STR = os.getenv(CONN_ENV) 


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
        self._message = message
        self._asq_message = asq_message


class _ASQConsumer(dramatiq.Consumer):
    def __init__(
        self,
        broker,
        queue_name: str,
        prefetch: int,
        timeout: int,
        dead_letter: bool = False,
    ) -> None:
        self.logger = broker.request.logger
        self.prefetch = min(prefetch, MAX_PREFETCH)
        self.timeout = timeout
        self.queue_name = queue_name
        # local cache
        self.messages: deque = deque()
        self.message_refc = 0
        self.dead_letter = dead_letter
        self.q_client = _get_client(queue_name)
        self.dlq_client = _get_dlq_client(queue_name) if dead_letter else None

    def ack(self, message: _ASQMessage) -> None:
        self.q_client.delete_message(message._asq_message)
        self.message_refc -= 1

    def nack(self, message: _ASQMessage) -> None:
        if self.dlq_client:
            self.dlq_client.send_message(message._message.encode())
        self.q_client.delete_message(message._asq_message)
        self.message_refc -= 1

    def requeue(self, messages: Iterable[_ASQMessage]) -> None:
        # No batch processing
        for message in messages:
            self.q_client.send_message(message._message.encode())
            self.q_client.delete_message(message._asq_message)
            self.message_refc -= 1

    def __next__(self) -> Optional[dramatiq.Message]:
        try:
            return self.messages.popleft()
        except IndexError:
            if self.message_refc < self.prefetch:
                messages = self.q_client.receive_messages(
                    messages_per_page=self.prefetch,
                    visibility_timeout=self.timeout,
                )
                for msg_batch in messages.by_page():
                    for _message in msg_batch:
                        dramatiq_message = dramatiq.Message.decode(_message.content)
                        self.messages.append(_ASQMessage(_message, dramatiq_message))
                        self.message_refc += 1
                time.sleep(MIN_TIMEOUT)
            try:
                return self.messages.popleft()
            except IndexError:
                return None


class ASQBroker(dramatiq.Broker):
    def __init__(
        self,
        *,
        dead_letter: bool = False,
        middleware=None,
    ) -> None:
        super().__init__(middleware=middleware)
        self.queues: set = set()
        self.dead_letter = dead_letter

    def consume(self, queue_name: str, prefetch: int = 1, timeout: int = 3000):
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

        self.logger.debug(f"Enqueueing message {message.message_id} on queue {queue_name}.")
        self.emit_before("enqueue", message, delay)
        q_client = _get_client(queue_name)
        q_client.send_message(message.encode(), visibility_timeout=delay_sec)
        self.emit_after("enqueue", message, delay)
        return message

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
