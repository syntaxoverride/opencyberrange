FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install Apache
RUN apt-get update && apt-get install -y apache2 && rm -rf /var/lib/apt/lists/*

# Create web root and hidden directories
RUN mkdir -p /var/www/html/admin /var/www/html/backup /var/www/html/config

# Create index page
RUN echo "<h1>Welcome to recon.lab</h1><p>This is a basic web server for directory enumeration practice.</p>" > /var/www/html/index.html

# Create hidden directory with flag
RUN echo "OCR{d1r3ct0ry_3num3r4t10n_b4s1c}" > /var/www/html/admin/flag.txt

# Create some other directories for practice
RUN echo "Backup files" > /var/www/html/backup/index.html
RUN echo "Configuration files" > /var/www/html/config/index.html

# Configure Apache
RUN a2enmod rewrite
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80
CMD ["apache2ctl", "-D", "FOREGROUND"]

