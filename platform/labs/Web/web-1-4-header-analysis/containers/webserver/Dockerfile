FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install Apache
RUN apt-get update && \
    apt-get install -y apache2 && \
    rm -rf /var/lib/apt/lists/*

# Enable required Apache modules
RUN a2enmod headers && \
    a2enmod rewrite

# Create custom Apache configuration with various headers (some secure, some not)
RUN echo '<VirtualHost *:80>' > /etc/apache2/sites-available/000-default.conf && \
    echo '    ServerAdmin webmaster@localhost' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    DocumentRoot /var/www/html' >> /etc/apache2/sites-available/000-default.conf && \
    echo '' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    # Information disclosure headers (intentional for learning)' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    Header set Server "Apache/2.4.54 (Ubuntu)"' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    Header set X-Powered-By "PHP/8.1.0"' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    Header set X-Backend-Server "web-server-01.internal.lab"' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    Header set X-Debug-Mode "enabled"' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    Header set X-Application-Version "1.2.3"' >> /etc/apache2/sites-available/000-default.conf && \
    echo '' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    # Missing security headers (intentional)' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    # No X-Frame-Options' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    # No X-Content-Type-Options' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    # No Content-Security-Policy' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    # No Strict-Transport-Security' >> /etc/apache2/sites-available/000-default.conf && \
    echo '' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    # Weak security headers' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    Header set X-XSS-Protection "0"' >> /etc/apache2/sites-available/000-default.conf && \
    echo '' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    ErrorLog ${APACHE_LOG_DIR}/error.log' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    CustomLog ${APACHE_LOG_DIR}/access.log combined' >> /etc/apache2/sites-available/000-default.conf && \
    echo '</VirtualHost>' >> /etc/apache2/sites-available/000-default.conf

# Create index page
RUN echo '<!DOCTYPE html>' > /var/www/html/index.html && \
    echo '<html>' >> /var/www/html/index.html && \
    echo '<head>' >> /var/www/html/index.html && \
    echo '    <title>Secure Application</title>' >> /var/www/html/index.html && \
    echo '</head>' >> /var/www/html/index.html && \
    echo '<body>' >> /var/www/html/index.html && \
    echo '    <h1>Welcome to secure.lab</h1>' >> /var/www/html/index.html && \
    echo '    <p>This application requires header analysis to find the flag.</p>' >> /var/www/html/index.html && \
    echo '    <p>Analyze the HTTP headers carefully!</p>' >> /var/www/html/index.html && \
    echo '</body>' >> /var/www/html/index.html && \
    echo '</html>' >> /var/www/html/index.html

# Create a special endpoint that reveals flag in headers
RUN echo '<?php' > /var/www/html/headers.php && \
    echo '// Flag is hidden in custom header' >> /var/www/html/headers.php && \
    echo 'header("X-Flag-Hint: Check internal server name");' >> /var/www/html/headers.php && \
    echo 'header("X-Internal-Server: web-server-01.internal.lab");' >> /var/www/html/headers.php && \
    echo 'header("X-Secret-Key: OCR{h34d3r_4n4lys1s_b4s1c}");' >> /var/www/html/headers.php && \
    echo 'echo "<h1>Header Analysis Endpoint</h1>";' >> /var/www/html/headers.php && \
    echo 'echo "<p>Check the HTTP response headers!</p>";' >> /var/www/html/headers.php && \
    echo '?>' >> /var/www/html/headers.php

# Install PHP for headers.php
RUN apt-get update && \
    apt-get install -y php libapache2-mod-php && \
    rm -rf /var/lib/apt/lists/*

# Set permissions
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80
CMD ["apache2ctl", "-D", "FOREGROUND"]

