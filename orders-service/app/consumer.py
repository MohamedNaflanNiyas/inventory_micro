# This script is a RabbitMQ consumer for the Orders Service. 
# It listens to the "order_inventory_queue" for messages related to order events, 
# specifically when an order is placed. Upon receiving a message, 
# it processes the order data, extracts the product ID and quantity, 
# and then makes an HTTP request to the Product Service to update the stock levels accordingly.
#  If the stock update is successful, it acknowledges the message; otherwise, it requeues the message for later processing.

import json 
import pika
import requests
import os

# Read the internal microservice URLS from envronment variables
PRODUCT_SERVICE_URL = os.getenv(
    "PRODUCT_SERVICE_URL",
    "http://fastapi_products_service:5002"
)

# Connect RabbitMQ
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host="rabbitmq_broker")
)

# Create a channel to communicate with RabbitMQ
channel = connection.channel()

# Create queue
channel.queue_declare(queue="order_inventory_queue", durable=True)

# Callback function to process messages from the queue
def callback(ch, method, properties, body):
    try:
        # parse the message body as JSON
        data = json.loads(body)

        # Extract product ID and quantity from the message
        product_id = data["product_id"]
        quantity = data["quantity"]

        print(f"Received Order Event: {data}")

        # Call Product Service
        response = requests.put(
            f"{PRODUCT_SERVICE_URL}/products/{product_id}/stock",
            params={"quantity": quantity},
            timeout=5
        )

        print("Stock Update Response:", response.status_code)

        # Acknowledge the message if stock update is successful, otherwise requeue it for later processing
        if response.status_code == 200:
            ch.basic_ack(delivery_tag = method.delivery_tag)
            print("Stock updated successfully for product_id:", product_id)
        else:
            print("Failed to update stock for product_id:", product_id, "Response:", response.text)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


    except Exception as e:
        print("Error processing message:", e)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

channel.basic_consume(
    queue="order_inventory_queue",
    on_message_callback=callback,
    auto_ack=False
)

print("Waiting for messages...")

channel.start_consuming()