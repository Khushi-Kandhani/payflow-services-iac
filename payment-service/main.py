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
QUEUE_NAME = "order-events"

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


def get_queue_url(sqs):
    while True:
        try:
            response = sqs.get_queue_url(QueueName=QUEUE_NAME)
            return response["QueueUrl"]
        except Exception as exc:
            print(f"Payment Service: Waiting for LocalStack SQS... ({exc})")
            time.sleep(3)


FAILURE_REASONS = [
    "Card declined by issuer",
    "Insufficient funds",
    "Payment gateway timeout",
    "Fraud check flagged transaction",
    "Card expired",
]


def process_payments():
    print("Payment Worker started successfully. Scanning for PENDING orders...")
    conn = get_db_connection()
    sqs = get_sqs_client()
    queue_url = get_queue_url(sqs)

    while True:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, amount, product_name FROM orders WHERE status = 'PENDING' ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED;"
            )
            order = cursor.fetchone()

            if order:
                order_id, amount, product_name = order
                print(f"Processing payment for Order ID {order_id} (Amount: ${amount})...")
                time.sleep(3)
                succeeded = random.random() > 0.3
                new_status = "SUCCESS" if succeeded else "FAILED"
                failure_reason = None if succeeded else random.choice(FAILURE_REASONS)
                cursor.execute(
                    "UPDATE orders SET status = %s, failure_reason = %s WHERE id = %s;",
                    (new_status, failure_reason, order_id)
                )
                conn.commit()

                event_payload = {
                    "event_type": "payment_completed",
                    "order_id": order_id,
                    "product_name": product_name,
                    "amount": float(amount),
                    "status": new_status,
                    "failure_reason": failure_reason,
                }
                sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(event_payload))
                print(f"Order ID {order_id} payment result: {new_status} — event pushed to SQS")

            cursor.close()
        except Exception as e:
            print(f"Error in execution loop: {e}")
            conn = get_db_connection()

        time.sleep(2)


if __name__ == "__main__":
    process_payments()
