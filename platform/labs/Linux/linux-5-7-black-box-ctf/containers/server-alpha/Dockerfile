FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN pip install --no-cache-dir flask

COPY app.py /app/app.py

WORKDIR /app

EXPOSE 80

CMD ["python3", "app.py"]
