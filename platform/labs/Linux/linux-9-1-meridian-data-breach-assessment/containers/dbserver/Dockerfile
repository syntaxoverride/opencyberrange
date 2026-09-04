FROM mysql:8.0

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV MYSQL_ROOT_PASSWORD=M3r1d14n_R00t_Int3rn4l#
ENV MYSQL_DATABASE=meridian_compliance

COPY init.sql /docker-entrypoint-initdb.d/init.sql

EXPOSE 3306
