import os
import time
import json
import boto3
import psycopg2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "payflow_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
QUEUE_NAME = "order-events"

# Global placeholder for the SQS Queue URL
QUEUE_URL = None

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )

def get_sqs_client():
    return boto3.client(
        "sqs",
        endpoint_url=AWS_ENDPOINT_URL,
        region_name=AWS_REGION,
        aws_access_key_id="mock",
        aws_secret_access_key="mock"
    )

# This block runs automatically when the FastAPI server starts up
@app.on_event("startup")
def startup_event():
    global QUEUE_URL
    print("Order Service: Connecting to LocalStack SQS...")
    sqs = get_sqs_client()
    
    # Retry loop to wait for LocalStack container to fully initialize
    for i in range(10):
        try:
            # Create the queue if it doesn't exist, or grab the URL if it does
            response = sqs.create_queue(QueueName=QUEUE_NAME)
            QUEUE_URL = response["QueueUrl"]
            print(f"Order Service: SQS Queue is ready at {QUEUE_URL}")
            break
        except Exception as e:
            print(f"Waiting for LocalStack SQS to start... ({e})")
            time.sleep(3)

class OrderCreate(BaseModel):
    product_name: str
    amount: float

@app.post("/orders", status_code=201)
def create_order(order: OrderCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. Save the order to PostgreSQL with status 'PENDING'
        cursor.execute(
            "INSERT INTO orders (product_name, amount, status) VALUES (%s, %s, 'PENDING') RETURNING id, status;",
            (order.product_name, order.amount)
        )
        order_id, status = cursor.fetchone()
        conn.commit()
        
        # 2. Package the data up as an event message
        message_body = {
            "order_id": order_id,
            "product_name": order.product_name,
            "amount": order.amount
        }
        
        # 3. Publish the event directly to our AWS SQS Queue
        if QUEUE_URL:
            sqs = get_sqs_client()
            sqs.send_message(
                QueueUrl=QUEUE_URL,
                MessageBody=json.dumps(message_body)
            )
            print(f"Order Service: Dispatched event to SQS for Order ID {order_id}")
        else:
            print("Warning: SQS Queue URL not initialized. Message not sent.")

        return {
            "order_id": order_id,
            "product_name": order.product_name,
            "amount": order.amount,
            "status": status,
            "message": "Order created successfully. Event published to SQS."
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
