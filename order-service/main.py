import os
import time
import json
import boto3
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# CORS - allows the React frontend (different origin/port) to call this API.
# Reads a comma-separated allow-list from CORS_ALLOWED_ORIGINS (set this to your
# real frontend URL(s) in any non-local environment). Defaults cover the two
# ways the frontend is served locally: `npm run dev` (Vite, :5173) and the
# built image served by nginx via docker-compose (:3000).
_default_origins = "http://localhost:5173,http://localhost:3000"
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", _default_origins).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "payflow_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# Two queues, two jobs:
# - ORDER_CREATED_QUEUE: consumed only by payment-service, one message per
#   order, deleted once picked up. This is what actually *drives* payment
#   processing - it's a work queue, not a broadcast.
# - EVENTS_QUEUE: consumed only by notification-service. Every service
#   publishes here so notifications can log the full order_created ->
#   payment_completed history. It's an event log, not a trigger.
# They used to be the same queue, which meant payment-service and
# notification-service were competing consumers on one queue - each message
# went to whichever one polled first, so the other silently missed it.
ORDER_CREATED_QUEUE = "order-created"
EVENTS_QUEUE = "order-events"

# Global placeholders for the SQS Queue URLs
ORDER_CREATED_QUEUE_URL = None
EVENTS_QUEUE_URL = None

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
    global ORDER_CREATED_QUEUE_URL, EVENTS_QUEUE_URL

    # NOTE: nothing in this repo previously created the `orders` table -
    # not here, not in terraform, not in a migration. Adding it here so the
    # service is actually runnable out of the box.
    print("Order Service: Ensuring database schema exists...")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            product_name VARCHAR(100) NOT NULL,
            amount DECIMAL NOT NULL,
            status VARCHAR(20) NOT NULL,
            failure_reason VARCHAR(100),
            created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Cheap forward-migration for anyone re-running this against an existing
    # database that predates the failure_reason column.
    cursor.execute("""
        ALTER TABLE orders ADD COLUMN IF NOT EXISTS failure_reason VARCHAR(100);
    """)
    # Cheap forward-migration for databases created before created_at was
    # switched from TIMESTAMP to TIMESTAMPTZ. Safe to run repeatedly - if the
    # column is already TIMESTAMPTZ this is a no-op.
    cursor.execute("""
        ALTER TABLE orders
        ALTER COLUMN created_at TYPE TIMESTAMPTZ
        USING created_at AT TIME ZONE 'UTC';
    """)
    conn.commit()
    cursor.close()
    conn.close()

    print("Order Service: Connecting to LocalStack SQS...")
    sqs = get_sqs_client()

    # Retry loop to wait for LocalStack container to fully initialize
    for i in range(10):
        try:
            ORDER_CREATED_QUEUE_URL = sqs.create_queue(QueueName=ORDER_CREATED_QUEUE)["QueueUrl"]
            EVENTS_QUEUE_URL = sqs.create_queue(QueueName=EVENTS_QUEUE)["QueueUrl"]
            print(f"Order Service: SQS queues ready ({ORDER_CREATED_QUEUE}, {EVENTS_QUEUE})")
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
            "event_type": "order_created",
            "order_id": order_id,
            "product_name": order.product_name,
            "amount": order.amount,
            "status": status,
        }
        
        # 3. Publish the event to both queues:
        #    - order-created: wakes up payment-service to actually process this order
        #    - order-events: logged by notification-service alongside every other event
        if ORDER_CREATED_QUEUE_URL and EVENTS_QUEUE_URL:
            sqs = get_sqs_client()
            sqs.send_message(QueueUrl=ORDER_CREATED_QUEUE_URL, MessageBody=json.dumps(message_body))
            sqs.send_message(QueueUrl=EVENTS_QUEUE_URL, MessageBody=json.dumps(message_body))
            print(f"Order Service: Dispatched order_created event for Order ID {order_id}")
        else:
            print("Warning: SQS queues not initialized. Message not sent.")

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


# These two GET endpoints didn't exist before - there was no way for any
# client (frontend or otherwise) to read order data back out, only create it.
@app.get("/orders")
def list_orders(limit: int = 50, status: str | None = None):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        if status:
            cursor.execute(
                "SELECT id, product_name, amount, status, failure_reason, created_at "
                "FROM orders WHERE status = %s ORDER BY created_at DESC LIMIT %s;",
                (status.upper(), limit)
            )
        else:
            cursor.execute(
                "SELECT id, product_name, amount, status, failure_reason, created_at "
                "FROM orders ORDER BY created_at DESC LIMIT %s;",
                (limit,)
            )
        rows = cursor.fetchall()
        return rows
    finally:
        cursor.close()
        conn.close()


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute(
            "SELECT id, product_name, amount, status, failure_reason, created_at "
            "FROM orders WHERE id = %s;",
            (order_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Order not found")
        return row
    finally:
        cursor.close()
        conn.close()
