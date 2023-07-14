import time

import dramatiq
import pytest
from azure.storage.queue import QueueClient

from dramatiq_azure import asq


def test_can_enqueue_and_process_messages(asq_broker, worker, queue_name):
    # Given an actor that stores incoming messages in a database
    db = []

    @dramatiq.actor(queue_name=queue_name)
    def do_work(x):
        db.append(x)

    # When I send that actor a message
    do_work.send(1)

    # And wait for it to be processed
    time.sleep(5)

    # Then the db should contain that message
    assert db == [1]


def test_limits_prefetch_if_consumer_queue_is_full(asq_broker, worker, queue_name):
    # Given that I have an actor that stores incoming messages in a database
    db = []

    # Set the worker prefetch limit to 1
    worker.queue_prefetch = 1

    # Add delay to actor logic to simulate processing time
    @dramatiq.actor(queue_name=queue_name)
    def do_work(x):
        db.append(x)
        time.sleep(10)

    # When I send that actor messages, it'll only prefetch and process a single message
    do_work.send(1)
    do_work.send(2)

    # Wait for message to be processed
    time.sleep(5)

    # Then the db should contain only that message, while it sleeps
    assert len(db) == 1


def test_can_enqueue_delayed_messages(asq_broker, worker, queue_name):
    # Given an actor that stores incoming messages in a database
    db = []

    @dramatiq.actor(queue_name=queue_name)
    def do_work(x):
        db.append(x)

    # When I send that actor a delayed message
    start_time = time.time()
    do_work.send_with_options(args=(1,), delay=5000)

    # And poll the database for a result each second
    for _ in range(60):
        if db:
            break

        time.sleep(1)

    # Then the db should contain that message
    assert db == [1]

    # And an appropriate amount of time should have passed
    delta = time.time() - start_time
    assert delta >= 5


def test_cant_delay_messages_for_longer_than_7_days(asq_broker, queue_name):
    # Given that I have an actor
    @dramatiq.actor(queue_name=queue_name)
    def do_work():
        pass

    # When I attempt to send that actor a message farther than 7 days into the future
    # Then I should get back a RuntimeError
    with pytest.raises(RuntimeError):
        do_work.send_with_options(delay=7 * 25 * 60 * 60 * 1000)


def test_cant_enqueue_messages_that_are_too_large(asq_broker, queue_name):
    # Given that I have an actor
    @dramatiq.actor(queue_name=queue_name)
    def do_work(s):
        pass

    # When I attempt to send that actor a message that's too large
    # Then a RuntimeError should be raised
    with pytest.raises(RuntimeError):
        do_work.send("a" * 64 * 1024)


def test_can_requeue_consumed_messages(asq_broker, queue_name):
    # Given an actor
    @dramatiq.actor(queue_name=queue_name)
    def do_work():
        pass

    # When I send that actor a message
    do_work.send()

    # And consume the message off the queue
    consumer = asq_broker.consume(queue_name)
    first_message = next(consumer)

    # And requeue the message
    consumer.requeue([first_message])

    # Then I should be able to consume the message again immediately
    second_message = next(consumer)
    assert first_message == second_message


def test_creates_dead_letter_queue():
    # Given that I have an SQS asq_broker with dead letters turned on
    asq_broker = asq.ASQBroker(dead_letter=True)

    # When I create a queue
    asq_broker.declare_queue("test")

    # Then a dead-letter queue should be created
    dlq = asq._get_dlq_client("test")
    assert isinstance(dlq, QueueClient)


def test_consumer_returns_none_with_empty_queue(queue_name):
    asq_broker = asq.ASQBroker(dead_letter=False)
    asq_broker.declare_queue(queue_name)

    # Consume a message off an empty queue
    consumer = asq_broker.consume(queue_name)
    first_message = next(consumer)

    # As the queue is empty message should be None
    assert not first_message

    # Try another time
    second_message = next(consumer)
    assert not second_message


def test_flush_queues_returns_no_message(asq_broker, queue_name):
    # Given an actor
    @dramatiq.actor(queue_name=queue_name)
    def do_work():
        pass

    # When I send that actor messages
    for _ in range(20):
        do_work.send()

    # And flush the queue
    asq_broker.flush_all()

    # Then the consumer returns no message
    consumer = asq_broker.consume(queue_name)
    assert not next(consumer)


def test_invalid_queue_fails(queue_name):
    # Given a broker
    asq_broker = asq.ASQBroker(dead_letter=False)

    # When I attempt to consume from an undeclared queue
    # Then an exception is raised
    with pytest.raises(dramatiq.errors.QueueNotFound):
        asq_broker.validate_queue(queue_name)


def test_redeclare_queue_passes(queue_name):
    # Given a broker and a declared queue
    asq_broker = asq.ASQBroker(dead_letter=True)
    asq_broker.declare_queue(queue_name)

    # When I attempt to redeclare an existing queue
    asq_broker.declare_queue(queue_name)
    asq_broker.declare_queue(queue_name)
    asq_broker.declare_queue(queue_name)

    # Then there's only one queue created
    assert len(asq_broker.queues) == 1


def test_nacked_messages_go_to_dlq(queue_name):
    # Given an actor and a consumer, and some queued messages
    asq_broker = asq.ASQBroker(dead_letter=True)
    asq_broker.declare_queue(queue_name)

    @dramatiq.actor(queue_name=queue_name)
    def do_work():
        pass

    for i in range(20):
        do_work.send(i)
    consumer = asq_broker.consume(queue_name)

    msg = next(consumer)
    msg_content = msg._asq_message.content
    assert msg.message_id in consumer.queued_message_ids

    # When I nack a message
    consumer.nack(msg)

    # Then the message is moved to the DL queue
    assert msg.message_id not in consumer.queued_message_ids
    dlq = asq._get_dlq_client(queue_name)
    dlqd_msg = dlq.receive_message()
    assert dlqd_msg.content == msg_content
