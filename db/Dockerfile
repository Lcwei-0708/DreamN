FROM mariadb:11.3

RUN apt-get update && apt-get install -y \
    cron \
    mariadb-client \
    && rm -rf /var/lib/apt/lists/*

CMD ["mariadbd"]