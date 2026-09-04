FROM mysql:8.0

ENV MYSQL_ROOT_PASSWORD=r00tN0v4T3ch_Int3rn4l#
ENV MYSQL_DATABASE=novatech

COPY init.sql /docker-entrypoint-initdb.d/init.sql

EXPOSE 3306
