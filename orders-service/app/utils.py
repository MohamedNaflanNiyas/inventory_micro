# Publishing Order Placed event to RabbitMQ when an order is created in the Orders Service. 
# This event will be consumed by the Inventory Service to update the stock levels accordingly.

import json 
import pika 

# Publish an order placed event to RabbitMQ
def publish_order_placed(product_id: int, quantity: int):
    # connect to the RabbitMQ container via the internal Docker network name
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='rabbitmq_broker')
    )
    # create a channel to communicate with RabbitMQ
    channel = connection.channel()

    # Declare a durable queue to restart the message survive broker
    channel.queue_declare(queue = 'order_inventory_queue', durable=True)

    message ={
        "product_id": product_id,
        "quantity": quantity
    }

    # publish the playload
    channel.basic_publish(
        exchange='',  #default exchange maps directly to queue name
        routing_key='order_inventory_queue',
        body=json.dumps(message),
        properties =pika.BasicProperties(
            delivery_mode = 2, #presistant message state on disk
        )
    )

    print(f"Product succesfully sent order event: {message}")
    connection.close()