import os
import time
import json
import boto3

AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
QUEUE_NAME = "order-events"


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
            print(f"Waiting for SQS queue to be ready... ({exc})")
            time.sleep(3)


def render_notification(event):
    order_id = event.get("order_id")
    product = event.get("product_name")
    amount = event.get("amount")
    status = event.get("status")
    event_type = event.get("event_type", "order_created")

    if event_type == "payment_completed":
        print("--- ✉️  PAYMENT STATUS NOTIFICATION ---")
        print(f"Order: #{order_id}")
        print(f"Status: {status}")
        print(f"Product: {product}")
        print(f"Amount: ${amount}")
        failure_reason = event.get("failure_reason")
        if status == "FAILED" and failure_reason:
            print(f"Reason: {failure_reason}")
        print("Message: The payment flow has completed.")
    else:
        print("--- ✉️  ORDER CREATED NOTIFICATION ---")
        print(f"Order: #{order_id}")
        print(f"Product: {product}")
        print(f"Amount: ${amount}")
        print("Message: Your order has entered the processing pipeline.")

    print("--------------------------------------")


def start_notification_worker():
    print("Notification Service: Initializing...")
    sqs = get_sqs_client()
    queue_url = get_queue_url(sqs)
    print(f"Notification Service started. Listening on queue: {queue_url}")

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=5
            )

            if "Messages" in response:
                for message in response["Messages"]:
                    body = json.loads(message["Body"])
                    render_notification(body)
                    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
        except Exception as e:
            print(f"Notification Worker Error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    start_notification_worker()
