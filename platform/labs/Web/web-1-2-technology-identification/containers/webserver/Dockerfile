FROM php:8.1-apache

# Install additional PHP extensions
RUN docker-php-ext-install mysqli && docker-php-ext-enable mysqli

# Enable Apache modules required for .htaccess
RUN a2enmod rewrite && \
    a2enmod headers

# Configure Apache to allow .htaccess files
# The php:8.1-apache image uses apache2.conf for Directory directives
# We need to ensure AllowOverride All is set for /var/www/html
RUN sed -i '/<Directory \/var\/www\/>/,/<\/Directory>/ s/AllowOverride None/AllowOverride All/' /etc/apache2/apache2.conf && \
    sed -i '/<Directory \/var\/www\/html>/,/<\/Directory>/ s/AllowOverride None/AllowOverride All/' /etc/apache2/apache2.conf
# If the Directory block doesn't exist, add it
RUN grep -q "<Directory /var/www/html>" /etc/apache2/apache2.conf || \
    (echo '' >> /etc/apache2/apache2.conf && \
     echo '<Directory /var/www/html>' >> /etc/apache2/apache2.conf && \
     echo '    Options Indexes FollowSymLinks' >> /etc/apache2/apache2.conf && \
     echo '    AllowOverride All' >> /etc/apache2/apache2.conf && \
     echo '    Require all granted' >> /etc/apache2/apache2.conf && \
     echo '</Directory>' >> /etc/apache2/apache2.conf)

# Set working directory
WORKDIR /var/www/html

# Create a WordPress-like application structure (but simpler)
# Note: Server header is set by Apache, not PHP
RUN echo '<?php' > index.php && \
    echo '// Simulated WordPress-like application' >> index.php && \
    echo 'header("X-Powered-By: PHP/8.1.0");' >> index.php && \
    echo 'header("X-Framework: WordPress/6.2.0");' >> index.php && \
    echo '?>' >> index.php && \
    echo '<!DOCTYPE html>' >> index.php && \
    echo '<html lang="en">' >> index.php && \
    echo '<head>' >> index.php && \
    echo '    <meta charset="UTF-8">' >> index.php && \
    echo '    <meta name="generator" content="WordPress 6.2.0">' >> index.php && \
    echo '    <title>Welcome to target.lab</title>' >> index.php && \
    echo '    <link rel="stylesheet" href="/wp-content/themes/twenty-twenty-three/style.css">' >> index.php && \
    echo '</head>' >> index.php && \
    echo '<body>' >> index.php && \
    echo '    <h1>Welcome to Our Website</h1>' >> index.php && \
    echo '    <p>This is a sample web application for technology identification practice.</p>' >> index.php && \
    echo '    <p>Can you identify what technologies are running?</p>' >> index.php && \
    echo '</body>' >> index.php && \
    echo '</html>' >> index.php

# Configure Apache to show version in Server header (for technology identification)
# Use sed to replace existing ServerTokens line or add it if missing
RUN sed -i 's/^ServerTokens.*/ServerTokens Full/' /etc/apache2/conf-available/security.conf || \
    echo 'ServerTokens Full' >> /etc/apache2/conf-available/security.conf

# Create WordPress-like directory structure
RUN mkdir -p /var/www/html/wp-content/themes/twenty-twenty-three && \
    mkdir -p /var/www/html/wp-admin && \
    mkdir -p /var/www/html/wp-includes

# Create a robots.txt file with technology hints
RUN echo 'User-agent: *' > /var/www/html/robots.txt && \
    echo 'Disallow: /wp-admin/' >> /var/www/html/robots.txt && \
    echo 'Disallow: /wp-includes/' >> /var/www/html/robots.txt

# Create a .htaccess file (Apache configuration)
# Simplified .htaccess - just RewriteEngine without RewriteBase to avoid errors
RUN echo '# WordPress' > /var/www/html/.htaccess && \
    echo 'RewriteEngine On' >> /var/www/html/.htaccess

# Create admin directory with flag
RUN mkdir -p /var/www/html/wp-admin && \
    echo "OCR{t3ch_1d3nt1f1c4t10n_b4s1c}" > /var/www/html/wp-admin/flag.txt

# Create a version file that reveals technology
RUN echo 'WordPress Version: 6.2.0' > /var/www/html/readme.html && \
    echo 'PHP Version: 8.1.0' >> /var/www/html/readme.html && \
    echo 'Apache Version: 2.4.54' >> /var/www/html/readme.html

# Set permissions
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80
CMD ["apache2-foreground"]

