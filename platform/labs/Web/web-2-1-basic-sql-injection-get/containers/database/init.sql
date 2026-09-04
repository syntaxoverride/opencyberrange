CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    full_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'user',
    flag VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username, password, email, full_name, role, flag) VALUES
('admin', 'admin123', 'admin@shopsecure.local', 'Administrator', 'admin', 'OCR{sql_1nj3ct10n_g3t_b4s1c}'),
('john.doe', 'password123', 'john@shopsecure.local', 'John Doe', 'user', NULL),
('jane.smith', 'securepass', 'jane@shopsecure.local', 'Jane Smith', 'user', NULL),
('bob.wilson', 'mypassword', 'bob@shopsecure.local', 'Bob Wilson', 'user', NULL);
