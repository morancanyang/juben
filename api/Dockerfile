FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/api
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["sh", "-c", "python -m api.migrate && uvicorn api.main:app --host 0.0.0.0 --port 8000"]
