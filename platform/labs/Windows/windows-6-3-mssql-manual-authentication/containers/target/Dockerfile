FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
RUN apt-get update && apt-get install -y mysql-server && rm -rf /var/lib/apt/lists/*

# Configure MySQL for remote access and file reading (override loaded after mysqld.cnf)
RUN printf '[mysqld]\nbind-address = 0.0.0.0\nsecure-file-priv =\ndefault-authentication-plugin = mysql_native_password\n' > /etc/mysql/mysql.conf.d/zzz-override.cnf

# Create remote user and seed flag
RUN service mysql start && sleep 2 && \
    mysql -e "CREATE USER 'sa'@'%' IDENTIFIED WITH mysql_native_password BY 'password'; GRANT ALL PRIVILEGES ON *.* TO 'sa'@'%'; FLUSH PRIVILEGES;" && \
    service mysql stop

RUN echo "OCR{mssql_m4nu4l_4uth}" > /tmp/flag.txt && chmod 644 /tmp/flag.txt
EXPOSE 3306
CMD service mysql start && tail -f /dev/null
