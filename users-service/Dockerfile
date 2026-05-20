FROM python:3.13.6-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5001

CMD ["flask", "--app", "app:create_app", "run", "--host=0.0.0.0", "--port=5001"]
