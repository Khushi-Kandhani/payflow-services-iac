import os
import time
import random
import psycopg2

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "payflow_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

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

def process_payments():
    print("Payment Worker started successfully. Scanning for PENDING orders...")
    conn = get_db_connection()
    
    while True:
        try:
            cursor = conn.cursor()
            # Fetch one pending order
            cursor.execute(
                "SELECT id, amount FROM orders WHERE status = 'PENDING' LIMIT 1 FOR UPDATE SKIP LOCKED;"
            )
            order = cursor.fetchone()
            
            if order:
                order_id, amount = order
                print(f"Processing payment for Order ID {order_id} (Amount: ${amount})...")
                
                # Simulate a network delay to an external payment gateway (Stripe/PayPal)
                time.sleep(3)
                
                # 70% Success / 30% Failure logic
                new_status = "SUCCESS" if random.random() > 0.3 else "FAILED"
                
                # Update order status
                cursor.execute(
                    "UPDATE orders SET status = %s WHERE id = %s;",
                    (new_status, order_id)
                )
                conn.commit()
                print(f"Order ID {order_id} payment result: {new_status}")
            
            cursor.close()
        except Exception as e:
            print(f"Error in execution loop: {e}")
            conn = get_db_connection() # Reconnect if connection dropped
            
        time.sleep(2) # Sleep for 2 seconds before checking for new orders again

if __name__ == "__main__":
    process_payments()
