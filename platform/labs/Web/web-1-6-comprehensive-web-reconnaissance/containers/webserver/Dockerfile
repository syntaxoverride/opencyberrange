FROM php:8.1-apache

# Install additional PHP extensions
RUN docker-php-ext-install mysqli && docker-php-ext-enable mysqli

# Enable Apache modules
RUN a2enmod rewrite && \
    a2enmod headers

# Set working directory
WORKDIR /var/www/html

# Create comprehensive vulnerable application
# This combines elements from all previous labs

# Create index page with technology hints
RUN echo '<?php' > index.php && \
    echo 'header("X-Powered-By: PHP/8.1.0");' >> index.php && \
    echo 'header("Server: Apache/2.4.54");' >> index.php && \
    echo 'header("X-Framework: Laravel/10.0.0");' >> index.php && \
    echo 'header("X-Application-Version: 2.1.3");' >> index.php && \
    echo '?>' >> index.php && \
    echo '<!DOCTYPE html>' >> index.php && \
    echo '<html lang="en">' >> index.php && \
    echo '<head>' >> index.php && \
    echo '    <meta charset="UTF-8">' >> index.php && \
    echo '    <meta name="generator" content="Laravel Framework">' >> index.php && \
    echo '    <title>Target Application</title>' >> index.php && \
    echo '</head>' >> index.php && \
    echo '<body>' >> index.php && \
    echo '    <h1>Welcome to target.lab</h1>' >> index.php && \
    echo '    <p>This is a comprehensive web application for reconnaissance practice.</p>' >> index.php && \
    echo '    <p>Perform a complete reconnaissance to find the flag.</p>' >> index.php && \
    echo '</body>' >> index.php && \
    echo '</html>' >> index.php

# Create hidden directories (directory enumeration)
RUN mkdir -p /var/www/html/admin /var/www/html/api /var/www/html/backup /var/www/html/config && \
    mkdir -p /var/www/html/uploads /var/www/html/private

# Create admin directory with hint
RUN echo '<h1>Admin Area</h1>' > /var/www/html/admin/index.html && \
    echo '<p>This is the admin area. Check for hidden files.</p>' >> /var/www/html/admin/index.html

# Create API endpoint (HTTP methods)
RUN echo '<?php' > /var/www/html/api/index.php && \
    echo 'header("Content-Type: application/json");' >> /var/www/html/api/index.php && \
    echo 'if ($_SERVER["REQUEST_METHOD"] === "OPTIONS") {' >> /var/www/html/api/index.php && \
    echo '    header("Allow: GET, POST, PUT, DELETE, OPTIONS");' >> /var/www/html/api/index.php && \
    echo '    echo json_encode(["message" => "Allowed methods: GET, POST, PUT, DELETE, OPTIONS"]);' >> /var/www/html/api/index.php && \
    echo '} else {' >> /var/www/html/api/index.php && \
    echo '    echo json_encode(["message" => "API endpoint", "method" => $_SERVER["REQUEST_METHOD"]]);' >> /var/www/html/api/index.php && \
    echo '}' >> /var/www/html/api/index.php && \
    echo '?>' >> /var/www/html/api/index.php

# Create backup directory
RUN echo 'Backup files' > /var/www/html/backup/index.html

# Create config directory with sensitive file
RUN echo 'Database Config' > /var/www/html/config/database.txt && \
    echo 'Flag hint: Check headers endpoint' >> /var/www/html/config/database.txt

# Create headers endpoint (header analysis)
RUN echo '<?php' > /var/www/html/headers.php && \
    echo 'header("X-Security-Headers: Missing");' >> /var/www/html/headers.php && \
    echo 'header("X-Debug-Mode: enabled");' >> /var/www/html/headers.php && \
    echo 'header("X-Internal-Path: /var/www/html/private/flag.txt");' >> /var/www/html/headers.php && \
    echo 'header("X-Flag-Hint: Check private directory");' >> /var/www/html/headers.php && \
    echo 'echo "<h1>Headers Endpoint</h1>";' >> /var/www/html/headers.php && \
    echo 'echo "<p>Check the HTTP response headers!</p>";' >> /var/www/html/headers.php && \
    echo '?>' >> /var/www/html/headers.php

# Create private directory with flag
RUN mkdir -p /var/www/html/private && \
    echo "OCR{c0mpr3h3ns1v3_r3c0n_b4s1c}" > /var/www/html/private/flag.txt && \
    echo "This is the flag file." >> /var/www/html/private/flag.txt

# Create robots.txt (technology identification)
RUN echo 'User-agent: *' > /var/www/html/robots.txt && \
    echo 'Disallow: /admin/' >> /var/www/html/robots.txt && \
    echo 'Disallow: /api/' >> /var/www/html/robots.txt && \
    echo 'Disallow: /backup/' >> /var/www/html/robots.txt && \
    echo 'Disallow: /config/' >> /var/www/html/robots.txt && \
    echo 'Disallow: /private/' >> /var/www/html/robots.txt && \
    echo 'Disallow: /uploads/' >> /var/www/html/robots.txt

# Create .htaccess file
RUN echo '# Laravel Framework' > /var/www/html/.htaccess && \
    echo 'RewriteEngine On' >> /var/www/html/.htaccess

# Create version file
RUN echo 'Application Version: 2.1.3' > /var/www/html/version.txt && \
    echo 'Framework: Laravel 10.0.0' >> /var/www/html/version.txt && \
    echo 'PHP Version: 8.1.0' >> /var/www/html/version.txt

# Set permissions
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80
CMD ["apache2-foreground"]

