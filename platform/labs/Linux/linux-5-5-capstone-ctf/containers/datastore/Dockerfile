FROM mysql:8.0

ENV MYSQL_ROOT_PASSWORD=Z3n1th_R00t_DB_2024#
ENV MYSQL_DATABASE=zenith

RUN printf 'CREATE DATABASE IF NOT EXISTS zenith;\n\
USE zenith;\n\
\n\
CREATE TABLE shipments (\n\
  id INT AUTO_INCREMENT PRIMARY KEY,\n\
  tracking_id VARCHAR(50),\n\
  origin VARCHAR(100),\n\
  destination VARCHAR(100),\n\
  status VARCHAR(50)\n\
);\n\
\n\
INSERT INTO shipments VALUES\n\
  (1,"ZG-2024-00142","Chicago, IL","Tokyo, JP","delivered"),\n\
  (2,"ZG-2024-00287","Los Angeles, CA","London, UK","in_transit"),\n\
  (3,"ZG-2024-00391","New York, NY","Sydney, AU","processing");\n\
\n\
CREATE TABLE flags (\n\
  id INT AUTO_INCREMENT PRIMARY KEY,\n\
  name VARCHAR(100),\n\
  value VARCHAR(255),\n\
  notes TEXT\n\
);\n\
\n\
INSERT INTO flags VALUES (1,"assessment","v1ct0ry","Capstone CTF final marker");\n\
\n\
CREATE USER IF NOT EXISTS "zenith_app"@"%%" IDENTIFIED WITH mysql_native_password BY "Z3n_DB_Pr0d#";\n\
GRANT SELECT ON zenith.* TO "zenith_app"@"%%";\n\
FLUSH PRIVILEGES;\n' > /docker-entrypoint-initdb.d/init.sql

EXPOSE 3306
