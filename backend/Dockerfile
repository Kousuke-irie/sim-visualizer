FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# 開発用の --reload は docker-compose.yml の command で付ける。インメモリストアのため worker は増やさない
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
