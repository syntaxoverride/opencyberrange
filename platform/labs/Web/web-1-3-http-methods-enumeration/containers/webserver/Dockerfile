FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install Apache and required modules
RUN apt-get update && \
    apt-get install -y apache2 && \
    rm -rf /var/lib/apt/lists/*

# Enable required Apache modules
RUN a2enmod rewrite && \
    a2enmod headers

# Create custom Apache configuration to allow various HTTP methods
RUN echo '<Directory /var/www/html>' > /etc/apache2/sites-available/000-default.conf && \
    echo '    Options Indexes FollowSymLinks' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    AllowOverride All' >> /etc/apache2/sites-available/000-default.conf && \
    echo '    Require all granted' >> /etc/apache2/sites-available/000-default.conf && \
    echo '</Directory>' >> /etc/apache2/sites-available/000-default.conf

# Create .htaccess to handle different HTTP methods
RUN echo 'RewriteEngine On' > /var/www/html/.htaccess && \
    echo '' >> /var/www/html/.htaccess && \
    echo '# Handle OPTIONS method' >> /var/www/html/.htaccess && \
    echo 'RewriteCond %{REQUEST_METHOD} ^OPTIONS$' >> /var/www/html/.htaccess && \
    echo 'RewriteRule ^(.*)$ methods.php?method=OPTIONS [L,QSA]' >> /var/www/html/.htaccess && \
    echo '' >> /var/www/html/.htaccess && \
    echo '# Handle PUT method' >> /var/www/html/.htaccess && \
    echo 'RewriteCond %{REQUEST_METHOD} ^PUT$' >> /var/www/html/.htaccess && \
    echo 'RewriteRule ^(.*)$ methods.php?method=PUT [L,QSA]' >> /var/www/html/.htaccess && \
    echo '' >> /var/www/html/.htaccess && \
    echo '# Handle DELETE method' >> /var/www/html/.htaccess && \
    echo 'RewriteCond %{REQUEST_METHOD} ^DELETE$' >> /var/www/html/.htaccess && \
    echo 'RewriteRule ^(.*)$ methods.php?method=DELETE [L,QSA]' >> /var/www/html/.htaccess && \
    echo '' >> /var/www/html/.htaccess && \
    echo '# Handle TRACE method' >> /var/www/html/.htaccess && \
    echo 'RewriteCond %{REQUEST_METHOD} ^TRACE$' >> /var/www/html/.htaccess && \
    echo 'RewriteRule ^(.*)$ methods.php?method=TRACE [L,QSA]' >> /var/www/html/.htaccess

# Install PHP for method handling
RUN apt-get update && \
    apt-get install -y php libapache2-mod-php && \
    rm -rf /var/lib/apt/lists/*

# Create methods.php to handle different HTTP methods
RUN echo '<?php' > /var/www/html/methods.php && \
    echo 'header("Content-Type: text/plain");' >> /var/www/html/methods.php && \
    echo '$method = $_GET["method"] ?? $_SERVER["REQUEST_METHOD"];' >> /var/www/html/methods.php && \
    echo '' >> /var/www/html/methods.php && \
    echo 'switch($method) {' >> /var/www/html/methods.php && \
    echo '    case "OPTIONS":' >> /var/www/html/methods.php && \
    echo '        header("Allow: GET, POST, PUT, DELETE, OPTIONS, TRACE");' >> /var/www/html/methods.php && \
    echo '        echo "Allowed methods: GET, POST, PUT, DELETE, OPTIONS, TRACE";' >> /var/www/html/methods.php && \
    echo '        break;' >> /var/www/html/methods.php && \
    echo '    case "PUT":' >> /var/www/html/methods.php && \
    echo '        $data = file_get_contents("php://input");' >> /var/www/html/methods.php && \
    echo '        file_put_contents("/var/www/html/uploads/flag.txt", "OCR{http_m3th0ds_3num3r4t10n}");' >> /var/www/html/methods.php && \
    echo '        echo "PUT method accepted. File created.";' >> /var/www/html/methods.php && \
    echo '        break;' >> /var/www/html/methods.php && \
    echo '    case "DELETE":' >> /var/www/html/methods.php && \
    echo '        echo "DELETE method accepted. Use with caution!";' >> /var/www/html/methods.php && \
    echo '        break;' >> /var/www/html/methods.php && \
    echo '    case "TRACE":' >> /var/www/html/methods.php && \
    echo '        echo "TRACE method accepted. Echoing request:";' >> /var/www/html/methods.php && \
    echo '        echo "\n";' >> /var/www/html/methods.php && \
    echo '        foreach ($_SERVER as $key => $value) {' >> /var/www/html/methods.php && \
    echo '            if (strpos($key, "HTTP_") === 0) {' >> /var/www/html/methods.php && \
    echo '                echo str_replace("_", "-", substr($key, 5)) . ": " . $value . "\n";' >> /var/www/html/methods.php && \
    echo '            }' >> /var/www/html/methods.php && \
    echo '        }' >> /var/www/html/methods.php && \
    echo '        break;' >> /var/www/html/methods.php && \
    echo '    default:' >> /var/www/html/methods.php && \
    echo '        echo "Method: " . $method;' >> /var/www/html/methods.php && \
    echo '}' >> /var/www/html/methods.php && \
    echo '?>' >> /var/www/html/methods.php

# Create uploads directory
RUN mkdir -p /var/www/html/uploads && \
    chmod 777 /var/www/html/uploads

# Create index page
RUN echo '<!DOCTYPE html>' > /var/www/html/index.html && \
    echo '<html>' >> /var/www/html/index.html && \
    echo '<head><title>API Endpoint</title></head>' >> /var/www/html/index.html && \
    echo '<body>' >> /var/www/html/index.html && \
    echo '    <h1>Welcome to api.lab</h1>' >> /var/www/html/index.html && \
    echo '    <p>This is an API endpoint for HTTP methods testing.</p>' >> /var/www/html/index.html && \
    echo '    <p>Try different HTTP methods to see what is allowed.</p>' >> /var/www/html/index.html && \
    echo '</body>' >> /var/www/html/index.html && \
    echo '</html>' >> /var/www/html/index.html

# Set permissions
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80
CMD ["apache2ctl", "-D", "FOREGROUND"]

