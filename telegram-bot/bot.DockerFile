FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ca-certificates

COPY russian_trusted_root_ca.cer /usr/local/share/ca-certificates/russian_trusted_root_ca.crt

RUN update-ca-certificates

# Установка зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && mkdir -p /logs \
    && chmod 777 /logs \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir ./bot
RUN mkdir ./videogeneration

COPY /bot/requirements.txt /bot/requirements.txt
COPY /videogeneration/requirements.txt /videogeneration/requirements.txt

RUN pip install -r /videogeneration/requirements.txt
RUN pip install -r /bot/requirements.txt
RUN pip install gigachat
RUN pip install sqlalchemy
RUN pip install asyncpg
RUN pip install pandas
RUN pip install psutil gputil
RUN pip install openpyxl

COPY . .
COPY main.py main.py

# Используем переменную из .env
ENV TZ=${TZ}

CMD ["python", "main.py"]