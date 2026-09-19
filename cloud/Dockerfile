FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY aria_cloud.py .

ENV ARIA_HOST=0.0.0.0
ENV ARIA_PORT=8000

EXPOSE 8000

CMD ["python", "aria_cloud.py"]
