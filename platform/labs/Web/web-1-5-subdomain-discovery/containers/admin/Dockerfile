FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install Apache
RUN apt-get update && \
    apt-get install -y apache2 && \
    rm -rf /var/lib/apt/lists/*

# Create admin subdomain page
RUN echo '<!DOCTYPE html>' > /var/www/html/index.html && \
    echo '<html>' >> /var/www/html/index.html && \
    echo '<head><title>Admin Panel</title></head>' >> /var/www/html/index.html && \
    echo '<body>' >> /var/www/html/index.html && \
    echo '    <h1>Admin Panel</h1>' >> /var/www/html/index.html && \
    echo '    <p>This is the admin subdomain.</p>' >> /var/www/html/index.html && \
    echo '    <p>Flag is in /flag.txt</p>' >> /var/www/html/index.html && \
    echo '</body>' >> /var/www/html/index.html && \
    echo '</html>' >> /var/www/html/index.html

# Create flag file
RUN echo "OCR{subd0m41n_d1sc0v3ry_b4s1c}" > /var/www/html/flag.txt

# Set permissions
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80
CMD ["apache2ctl", "-D", "FOREGROUND"]

