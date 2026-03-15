# 🌾 Weather-Based Crop Suggestion System

A Flask web application that helps farmers and agricultural users identify the most suitable crops to grow based on real-time weather conditions, rainfall data, and soil type.

---

## 📌 Features

- **Weather Data Fetching** — Retrieves live temperature and humidity for any city using the OpenWeatherMap API
- **Rainfall Analysis** — Pulls yearly precipitation data via the Open-Meteo Archive API
- **Smart Crop Suggestions** — Matches weather + soil type against a crop database to recommend suitable crops
- **Crop Images** — Displays visual references for each suggested crop using the Unsplash API
- **Suggestion History** — Users can view all their previous crop suggestions
- **User Authentication** — Secure signup and login with hashed passwords and OTP verification
- **Admin Panel** — Admins can manage the crop database (add, edit, delete crops) and view registered users
- **CSRF Protection** — All forms are protected using Flask-WTF

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Database | MySQL (via PyMySQL) |
| Authentication | Werkzeug password hashing, OTP |
| External APIs | OpenWeatherMap, Open-Meteo, Unsplash |
| Frontend | HTML, CSS (Jinja2 templates) |
| Security | Flask-WTF CSRF Protection |

---

## 📁 Project Structure

```
project911/
├── app.py                      # Main Flask application
├── templates/
│   ├── home.html
│   ├── login.html
│   ├── signup.html
│   ├── verify_otp.html
│   ├── dashboard.html
│   ├── weatherinput.html
│   ├── crop_suggestion.html
│   ├── previous_suggestions.html
│   ├── admin_login.html
│   └── admin_dashboard.html
└── static/
    └── (images and assets)
```

---

## ⚙️ Setup & Installation

### Prerequisites

- Python 3.8+
- MySQL Server
- pip



### 2. Install Dependencies

```bash
pip install flask flask-wtf pymysql werkzeug requests
```

### 3. Configure the Database

Create a MySQL database named `users_db` and run the following SQL to set up the required tables:

```sql
CREATE DATABASE users_db;
USE users_db;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE crops (
    crop_id INT AUTO_INCREMENT PRIMARY KEY,
    crop_name VARCHAR(100) NOT NULL,
    temp_min FLOAT,
    temp_max FLOAT,
    rainfall_min FLOAT,
    rainfall_max FLOAT,
    avg_rainfall FLOAT,
    soil_type VARCHAR(100),
    description TEXT
);

CREATE TABLE weather_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    city VARCHAR(100),
    temperature FLOAT,
    humidity FLOAT,
    rainfall VARCHAR(50),
    soil VARCHAR(100),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE suggestions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    crop_name VARCHAR(100),
    temperature FLOAT,
    humidity FLOAT,
    rainfall FLOAT,
    soil_type VARCHAR(100),
    suggested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 4. Configure API Keys

Open `app.py` and replace the placeholder values with your actual API keys:

```python
app.secret_key = "your_secret_key"           # Change to a strong random secret
WEATHER_API_KEY = "your_openweathermap_key"  # https://openweathermap.org/api
UNSPLASH_ACCESS_KEY = "your_unsplash_key"    # https://unsplash.com/developers
```

> ⚠️ **Important:** Never commit real API keys to version control. Use environment variables or a `.env` file in production.

### 5. Run the Application

```bash
python app.py
```

Visit `http://127.0.0.1:5000` in your browser.

---

## 🔑 Usage

### User Flow

1. **Register** at `/signup` with your name, email, and password
2. **Verify OTP** sent to your email
3. **Log in** at `/login`
4. **Enter your location** (city name or coordinates) and soil type on the weather input page
5. View **live weather data** and **annual rainfall** for your location
6. Get **crop suggestions** tailored to your conditions
7. Browse **previous suggestions** at any time from your dashboard

### Admin Flow

1. Visit `/admin_login` and log in with admin credentials
2. **Manage crops** — add new crops with their temperature, rainfall, and soil requirements
3. **Edit or delete** existing crops from the dashboard
4. **View all registered users**

---

## 🌐 API Integrations

| API | Purpose | Docs |
|---|---|---|
| OpenWeatherMap | Current weather (temp, humidity) + geocoding | [openweathermap.org](https://openweathermap.org/api) |
| Open-Meteo Archive | Historical yearly rainfall data | [open-meteo.com](https://open-meteo.com) |
| Unsplash | Crop images for suggestions | [unsplash.com/developers](https://unsplash.com/developers) |

---

## 🔒 Security Notes

- User passwords are hashed using `werkzeug.security` (PBKDF2)
- All forms are CSRF-protected via `Flask-WTF`
- Admin passwords are currently stored as plain text in the DB — **it is strongly recommended to hash admin passwords before deploying to production**
- Replace hardcoded API keys with environment variables before production deployment:

```python
import os
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")
app.secret_key = os.environ.get("SECRET_KEY")
```

---

## 📸 Screenshots

> *(Add screenshots of the home page, weather input, crop suggestion results, and admin dashboard here)*

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
