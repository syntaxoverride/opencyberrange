<?php
session_start();

// Connect to database
$db_host = getenv("DB_HOST") ?: "db-mysql";
$conn = new mysqli($db_host, "webapp", "webapp123", "shopdb");

if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// Handle login
$error = "";
$logged_in = false;
$user = null;

if ($_SERVER["REQUEST_METHOD"] == "POST" && isset($_POST["username"]) && isset($_POST["password"])) {
    $username = $_POST["username"];
    $password = $_POST["password"];

    // VULNERABLE: Direct string concatenation - SQL Injection vulnerability
    $query = "SELECT * FROM users WHERE username = '" . $username . "' AND password = '" . $password . "'";

    $result = $conn->query($query);

    if ($result && $result->num_rows > 0) {
        $user = $result->fetch_assoc();
        $_SESSION["user_id"] = $user["id"];
        $_SESSION["username"] = $user["username"];
        $_SESSION["logged_in"] = true;
        $logged_in = true;
    } else {
        $error = "Invalid username or password";
    }
}

// Check if already logged in
if (isset($_SESSION["logged_in"]) && $_SESSION["logged_in"]) {
    $user_id = $_SESSION["user_id"];
    $result = $conn->query("SELECT * FROM users WHERE id = " . intval($user_id));
    if ($result && $result->num_rows > 0) {
        $user = $result->fetch_assoc();
        $logged_in = true;
    }
}

// Handle logout
if (isset($_GET["logout"])) {
    session_destroy();
    header("Location: /");
    exit;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShopSecure - Login</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 40px;
            max-width: 500px;
            width: 100%;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            text-align: center;
        }
        .subtitle {
            color: #666;
            text-align: center;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: bold;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus,
        input[type="password"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        .error {
            background: #fee;
            color: #c33;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            border: 1px solid #fcc;
        }
        .dashboard {
            text-align: center;
        }
        .welcome {
            color: #667eea;
            font-size: 24px;
            margin-bottom: 20px;
        }
        .user-info {
            background: #f5f5f5;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
            text-align: left;
        }
        .user-info p {
            margin: 10px 0;
            color: #333;
        }
        .user-info strong {
            color: #667eea;
        }
        .flag {
            background: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border: 2px solid #c3e6cb;
            font-weight: bold;
            font-size: 18px;
        }
        .logout {
            display: inline-block;
            margin-top: 20px;
            padding: 10px 20px;
            background: #dc3545;
            color: white;
            text-decoration: none;
            border-radius: 5px;
        }
        .logout:hover {
            background: #c82333;
        }
    </style>
</head>
<body>
    <div class="container">
        <?php if ($logged_in && $user): ?>
            <div class="dashboard">
                <h1 class="welcome">Welcome, <?php echo htmlspecialchars($user["full_name"]); ?>!</h1>
                <div class="user-info">
                    <p><strong>Username:</strong> <?php echo htmlspecialchars($user["username"]); ?></p>
                    <p><strong>Email:</strong> <?php echo htmlspecialchars($user["email"]); ?></p>
                    <p><strong>Role:</strong> <?php echo htmlspecialchars($user["role"]); ?></p>
                    <p><strong>User ID:</strong> <?php echo htmlspecialchars($user["id"]); ?></p>
                    <?php if ($user["flag"]): ?>
                        <div class="flag">
                            Flag: <?php echo htmlspecialchars($user["flag"]); ?>
                        </div>
                    <?php endif; ?>
                </div>
                <a href="?logout=1" class="logout">Logout</a>
            </div>
        <?php else: ?>
            <h1>ShopSecure</h1>
            <p class="subtitle">Employee Portal - Please login to continue</p>

            <?php if ($error): ?>
                <div class="error"><?php echo htmlspecialchars($error); ?></div>
            <?php endif; ?>

            <form method="POST" action="">
                <div class="form-group">
                    <label for="username">Username:</label>
                    <input type="text" id="username" name="username" required autofocus>
                </div>
                <div class="form-group">
                    <label for="password">Password:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <button type="submit">Login</button>
            </form>
        <?php endif; ?>
    </div>
</body>
</html>
<?php
$conn->close();
?>
