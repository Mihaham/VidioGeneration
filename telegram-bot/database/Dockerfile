FROM postgres:latest

# Копируем скрипт инициализации
COPY init-user-db.sh /docker-entrypoint-initdb.d/

# Даем права на выполнение скрипта
RUN chmod +x /docker-entrypoint-initdb.d/init-user-db.sh

# Точка монтирования для данных
VOLUME /var/lib/postgresql/data