import json
import pika
import requests
import os

PRODUCT_SERVICE_URL = os.getenv(
    "PRODUCT_SERVICE_URL",
    "http://fastapi_products_service:5002"
)

# Connect RabbitMQ
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host="rabbitmq_broker")
)

channel = connection.channel()

# Create queue
channel.queue_declare(queue="order_inventory_queue", durable=True)


def callback(ch, method, properties, body):

    data = json.loads(body)

    product_id = data["product_id"]
    quantity = data["quantity"]

    print(f"Received Order Event: {data}")

    # Call Product Service
    response = requests.put(
        f"{PRODUCT_SERVICE_URL}/products/{product_id}/stock",
        params={"quantity": quantity}
    )

    print("Stock Update Response:", response.status_code)


channel.basic_consume(
    queue="order_inventory_queue",
    on_message_callback=callback,
    auto_ack=True
)

print("Waiting for messages...")

channel.start_consuming()