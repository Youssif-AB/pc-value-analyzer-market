FROM python:3.11-slim
RUN pip install --no-cache-dir "mlflow>=3,<4" "psycopg[binary]>=3.2,<4"
RUN mkdir -p /mlartifacts
EXPOSE 5000
CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]
