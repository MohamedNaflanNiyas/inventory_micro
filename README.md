# Inventory Management

## users-service
## products-service
## orders-service



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

#### 2. products-service : FastAPI
==> To create new products : http://localhost:5002/products
==> To get all products : http://localhost:5002/products
==> To get product by ID : http://localhost:5002/products/1

#### 3. orders-service : FastAPI
==> To create new orders : http://localhost:5003/orders
