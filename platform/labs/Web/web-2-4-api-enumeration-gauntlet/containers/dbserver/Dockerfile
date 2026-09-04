FROM mysql:8.0

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

ENV MYSQL_ROOT_PASSWORD=r00tSt0n3br1dg3_Int3rn4l#
ENV MYSQL_DATABASE=stonebridge

COPY init.sql /docker-entrypoint-initdb.d/init.sql

EXPOSE 3306
