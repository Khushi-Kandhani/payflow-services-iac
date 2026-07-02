import os
import time
import random
import json
import boto3
import psycopg2

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "payflow_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# order-created is a dedicated work queue: one order_created message per
# order, consumed only here. This is what actually triggers processing now -
# previously this worker just polled Postgres for any PENDING row every 2s,
# which meant the SQS queue existed but wasn't driving anything.
ORDER_CREATED_QUEUE = "order-created"
# order-events is the shared log every service publishes to, consumed only
# by notification-service. We still publish payment_completed here.
EVENTS_QUEUE = "order-events"


def get_db_connection():
    while True:
        try:
            conn = psycopg2.connect(
                host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
            )
            return conn
        except psycopg2.OperationalError:
            print("Payment Service: Database not ready, retrying in 2 seconds...")
            time.sleep(2)


def get_sqs_client():
    return boto3.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION,
        aws_access_key_id="mock",
        aws_secret_access_key="mock"
    )


def get_queue_url(sqs, queue_name):
    while True:
        try:
            response = sqs.get_queue_url(QueueName=queue_name)
            return response["QueueUrl"]
        except Exception as exc:
            print(f"Payment Service: Waiting for LocalStack SQS ({queue_name})... ({exc})")
            time.sleep(3)


FAILURE_REASONS = [
    "Card declined by issuer",
    "Insufficient funds",
    "Payment gateway timeout",
    "Fraud check flagged transaction",
    "Card expired",
]


def process_order(conn, sqs, events_queue_url, order_id):
    """
    Locks and processes a single order by id. Uses FOR UPDATE SKIP LOCKED as
    a safety net, not the primary trigger: SQS at-least-once delivery means
    the same order_created message can arrive twice, and this makes a
    duplicate delivery a safe no-op instead of a double-charge.
    """
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, amount, product_name FROM orders "
            "WHERE id = %s AND status = 'PENDING' FOR UPDATE SKIP LOCKED;",
            (order_id,)
        )
        order = cursor.fetchone()

        if not order:
            # Either already processed by a duplicate delivery, or someone
            # else has it locked right now. Nothing to do.
            cursor.close()
            return

        db_order_id, amount, product_name = order
        print(f"Processing payment for Order ID {db_order_id} (Amount: ${amount})...")
        time.sleep(3)
        succeeded = random.random() > 0.3
        new_status = "SUCCESS" if succeeded else "FAILED"
        failure_reason = None if succeeded else random.choice(FAILURE_REASONS)
        cursor.execute(
            "UPDATE orders SET status = %s, failure_reason = %s WHERE id = %s;",
            (new_status, failure_reason, db_order_id)
        )
        conn.commit()

        event_payload = {
            "event_type": "payment_completed",
            "order_id": db_order_id,
            "product_name": product_name,
            "amount": float(amount),
            "status": new_status,
            "failure_reason": failure_reason,
        }
        sqs.send_message(QueueUrl=events_queue_url, MessageBody=json.dumps(event_payload))
        print(f"Order ID {db_order_id} payment result: {new_status} — event pushed to SQS")
    finally:
        cursor.close()


def process_payments():
    print("Payment Worker started successfully. Listening on the order-created queue...")
    conn = get_db_connection()
    sqs = get_sqs_client()
    order_created_queue_url = get_queue_url(sqs, ORDER_CREATED_QUEUE)
    events_queue_url = get_queue_url(sqs, EVENTS_QUEUE)

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=order_created_queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=10,
            )
            messages = response.get("Messages", [])
            if not messages:
                continue

            for message in messages:
                body = json.loads(message["Body"])
                order_id = body.get("order_id")
                if order_id is not None:
                    process_order(conn, sqs, events_queue_url, order_id)
                sqs.delete_message(
                    QueueUrl=order_created_queue_url,
                    ReceiptHandle=message["ReceiptHandle"],
                )
        except Exception as e:
            print(f"Error in execution loop: {e}")
            conn = get_db_connection()
            time.sleep(2)


if __name__ == "__main__":
    process_payments()
