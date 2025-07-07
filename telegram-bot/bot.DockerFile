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

# Установка базовых зависимостей
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagickwand-dev \
    imagemagick \
    ghostscript \
    fonts-dejavu \
    fonts-dejavu-extra \
    fonts-freefont-ttf \
    fonts-noto-cjk \
    fonts-noto-core

RUN apt-get install build-essential -y # Installs g++ and other tools

RUN mkdir ./bot
RUN mkdir ./videogeneration

COPY /bot/requirements.txt /bot/requirements.txt
COPY /videogeneration/requirements.txt /videogeneration/requirements.txt

RUN pip install -r /videogeneration/requirements.txt
RUN pip install -r /bot/requirements.txt
RUN pip install gigachat
RUN pip install sqlalchemy
RUN pip install asyncpg
RUN pip install pandas==1.5.3
RUN pip install psutil gputil
RUN pip install openpyxl
RUN pip install moviepy==1.0.3 speechrecognition pydub

COPY bot/ bot/
COPY database/ database/
COPY videogeneration/ videogeneration/
COPY fonts/ fonts/
COPY russian_trusted_root_ca.cer russian_trusted_root_ca.cer
COPY client_secrets.json client_secrets.json
COPY main.py main.py

# Используем переменную из .env
ENV TZ=${TZ}

CMD ["python", "main.py"]