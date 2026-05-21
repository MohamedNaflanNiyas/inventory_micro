# consumer file that wait for RabbitMQ messages. 
#  When a message arrives it open a raw connection to your products database to decrement the inventory stock levels

import json
import pika
import time
import os
import psycopg2

# Fallback to standard local address strings if envirinment variable are missing
DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@postgres_db:5432/products_db"
)

def deduct_inventory(product_id: int, quantity:int):
    # executes atomic SQL commands to decrement product stock levels
    connection = None
    try:
        # connect to DB using connection parameters parased from URL
        connection = psycopg2.connect(DB_URL)
        cursor = connection.cursor()
        
        # Atomically deduct stock only if sufficient stock exists
        query = """
            UPDATE products
            SET stock = stock -%s
            WHERE id = %s AND stock >= %s;
        """

        cursor.execute(query, (quantity, product_id, quantity))
        connection.commit()

        if cursor.rowcount > 0:
            print(f"Database updated: Detucted {quantity} items from product ID : {product_id}")
        else:
            print(f"Deficit Warning: Product ID {product_id} has insufficient stock or product doesn't exists")

        cursor.close()
    except Exception as e:
        print(f" Worker database exception: {e}" )
    finally:
        if connection:
            connection.close()

# To handle individual incoming queue message deliveries
def callback(ch, method, properties, body):
    try:
        payload = json.loads(body.decode())
        print("f - Consumer pulled order event: {payload}")

        # process dB operation
        deduct_inventory(product_id = payload['product_id'], quantity=payload['quantity'])

        # Acknoledge completion back to RabbitMQ to securely strip the message from the queue
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error processing queue payload: {e}")

# initializes RabbitMQ connection listener loops
def start_worker():
    print("Worker process sleeping for 10 seconds to allow RabbitMQ startup...")
    time.sleep(10)

    try: 
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq_broker'))
        channel = connection.channel()

        # keep consistent declaration configurations
        channel.queue_declare(queue='order_inventory_quue', durable=True)

        # only deliver 1 unackowledged message to this consumer container at a time
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue='order_inventory_quue', on_message_callback=callback)

        print(" consumer setup completed... Listing to inventory messages")
        channel.start_consuming()
    except Exception as e:
        print(f"Connection block RabbitMQ aborted: {e}")

if __name__ =="__main__":
    start_worker()