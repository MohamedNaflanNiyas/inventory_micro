# Inventory Management

# System Architecture Overview

## Introduction

This project is a containerized microservices based application built using Flask, FastAPI, PostgreSQL, RabbitMQ, and Docker. The system is designed following microservices and event driven architecture principles, where each service has a dedicated responsibility and communicates with other services through REST APIs and message queues.

The architecture consists of the following components:

* Users Service (Flask)
* Products Service (FastAPI)
* Orders Service (FastAPI)


# Users Service

## Purpose

The Users Service is responsible for managing user related operations within the system. It provides APIs to create, retrieve, update, and delete user information.

## Technologies

* Flask
* Flask-SQLAlchemy
* PostgreSQL

## Responsibilities

* Create new users
* Retrieve user information
* Update user details (User Name)
* Delete users
* Validate user existence for order processing

## Database

The service stores data in the users_db PostgreSQL database.


## Example Workflow

1. Client sends a request to create a user.
2. Users Service validates the data.
3. User information is stored in PostgreSQL.
4. The created user is returned to the client.


# Products Service

## Purpose

The Products Service manages product inventory and stock information.

It provides APIs for product management and inventory updates.

## Technologies

* FastAPI
* SQLAlchemy Async ORM
* PostgreSQL
* Pydantic

## Responsibilities

* Create products
* Retrieve products
* Update product stock
* Delete products
* Maintain inventory availability

## Database

The service stores data in the products_db PostgreSQL database.

## Example Workflow

1. Product is created through the API.
2. Product details are stored in PostgreSQL.
3. Inventory can be increased or decreased through stock management endpoints.
4. Product information is returned to requesting services.

# Orders Service

## Purpose

The Orders Service acts as the central orchestrator of the system.

It coordinates communication between the Users Service and Products Service when processing orders.

## Technologies

* FastAPI
* HTTP Client Communication
* RabbitMQ

## Responsibilities

* Receive order requests
* Validate users
* Validate products
* Publish order events to RabbitMQ
* Coordinate the order lifecycle

## Order Processing Workflow

### Step 1: User Validation

The Orders Service first communicates with the Users Service to verify that the requested user exists.

### Step 2: Product Validation

The Orders Service then checks product information through the Products Service.

### Step 3: Event Publication

Once validations are successful, the Orders Service publishes an order event to RabbitMQ for asynchronous processing.

Instead of directly updating inventory, it delegates this responsibility to a background consumer.

This keeps the API responsive and scalable.

# RabbitMQ Message Broker

## Purpose

RabbitMQ acts as the communication layer between services.

It enables asynchronous processing by storing messages in queues until they are processed by consumers.

## Responsibilities

* Receive order events from Orders Service
* Store messages safely in queues
* Deliver messages to consumers
* Ensure reliable communication between services

## Benefits

* Decouples services
* Improves scalability
* Prevents blocking operations
* Increases system reliability


# Orders Consumer Service

## Purpose

The Orders Consumer is a background worker that continuously listens for messages from RabbitMQ.

It processes order events independently from the Orders Service.

## Technologies

* Python
* RabbitMQ
* Docker

## Responsibilities

* Consume order events
* Update product inventory
* Call Products Service APIs
* Acknowledge completed messages

## Consumer Workflow

### Step 1

RabbitMQ receives an order event.

### Step 2

The Consumer retrieves the message from the queue.

### Step 3

The Consumer extracts product information and quantity.

### Step 4

The Consumer calls the Products Service stock deduction endpoint.

### Step 5

After successful processing, the Consumer acknowledges the message.

### Step 6

RabbitMQ removes the message from the queue.

This ensures that every order event is processed reliably without affecting API response times.

# PostgreSQL Database

## Purpose

PostgreSQL serves as the primary data storage layer.

The project uses a single PostgreSQL container containing two separate databases:

### users_db

Stores user related information.

### products_db

Stores product and inventory related information.

This separation allows each microservice to maintain ownership of its own data while sharing the same database server.

# Complete System Flow

1. Client places an order.
2. Orders Service receives the request.
3. Orders Service validates the user through Users Service.
4. Orders Service validates the product through Products Service.
5. Orders Service publishes an order event to RabbitMQ.
6. RabbitMQ stores the event in a queue.
7. Orders Consumer retrieves the event.
8. Orders Consumer calls Products Service.
9. Products Service deducts inventory stock.
10. Consumer acknowledges the message.
11. RabbitMQ removes the processed event.


## DOCKER

##### ->  docker-compose down
### 
##### ->  To down the version : docker-compose down -v
##### ->  docker-compose build --no-cache 
##### ->  docker-compose up --build 
##### -> docker-compose up

#### Run a Single Specific Service from a Compose file -> docker-compose start ServiceName

#### To Update single services 
->  docker-compose up -d --build orders-service


### END POINT LINKS:

#### 1. users-service : Flask
==> To create new users : http://localhost:5001/users
==> To get all users : http://localhost:5001/users
==> To get user by ID : http://localhost:5001/users/1
==> to Update Username: http://localhost:5001/users/update/2
==> To delete User: http://localhost:5001/users/delete/3

#### 2. products-service : FastAPI
==> To create new products : http://localhost:5002/products
==> To get all products : http://localhost:5002/products
==> To get product by ID : http://localhost:5002/products/1
==> To Update product stock: http://localhost:5002/products/add-stock/1
==> To delete product: http://localhost:5002/products/1


#### 3. orders-service : FastAPI
==> To create new orders : http://localhost:5003/orders
==> To get all orders : http://localhost:5003/orders
==> To get order by ID : http://localhost:5003/orders/1
==> To Update order by ID : http://localhost:5003/orders/1
==> To Delete order by ID : http://localhost:5003/orders/1
