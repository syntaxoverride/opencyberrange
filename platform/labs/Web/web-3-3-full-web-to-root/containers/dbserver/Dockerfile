FROM mysql:8.0

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV MYSQL_ROOT_PASSWORD=r00tM3dC0r3_Int3rn4l#
ENV MYSQL_DATABASE=medcore

COPY init.sql /docker-entrypoint-initdb.d/init.sql

EXPOSE 3306
