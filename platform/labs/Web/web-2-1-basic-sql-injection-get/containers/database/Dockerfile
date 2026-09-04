FROM mysql:8.0

# Set root password
ENV MYSQL_ROOT_PASSWORD=rootpass
ENV MYSQL_DATABASE=shopdb
ENV MYSQL_USER=webapp
ENV MYSQL_PASSWORD=webapp123

# Create database schema and data
COPY init.sql /docker-entrypoint-initdb.d/init.sql

EXPOSE 3306
