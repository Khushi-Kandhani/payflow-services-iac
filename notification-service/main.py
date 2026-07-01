import os
import time
import json
import boto3

AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
QUEUE_NAME = "order-events"

def get_sqs_client():
    # Connect to LocalStack SQS
    return boto3.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION,
        aws_access_key_id="mock",
        aws_secret_access_key="mock"
    )

def start_notification_worker():
    print("Notification Service: Initializing...")
    sqs = get_sqs_client()
    
    # Ensure the queue exists before trying to read from it
    while True:
        try:
            queue_url = sqs.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"]
            break
        except Exception:
            print("Waiting for SQS queue to be created by Order Service...")
            time.sleep(3)

    print(f"Notification Service started. Listening on queue: {queue_url}")

    while True:
        try:
            # Poll for messages from the SQS queue
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=5 # Long-polling reduces CPU usage
            )

            if "Messages" in response:
                for message in response["Messages"]:
                    # Parse the message payload
                    body = json.loads(message["Body"])
                    order_id = body.get("order_id")
                    product = body.get("product_name")
                    amount = body.get("amount")

                    print(f"--- ✉️  SENDING EMAIL NOTIFICATION ---")
                    print(f"To: customer@payflow.com")
                    print(f"Subject: Order #{order_id} Received!")
                    print(f"Body: Thank you for purchasing {product} (${amount}).")
                    print(f"--------------------------------------")

                    # Crucial: Delete the message from the queue so no one else processes it
                    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
            
        except Exception as e:
            print(f"Notification Worker Error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    start_notification_worker()
