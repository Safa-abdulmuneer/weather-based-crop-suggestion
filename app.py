from flask import Flask, render_template, request, redirect, flash, session, url_for
import requests
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
from flask_wtf.csrf import CSRFProtect


app = Flask(__name__)
csrf = CSRFProtect(app)
app.secret_key = "your_secret_key"  # Change this to a secure key

# API Keys & URLs
WEATHER_API_KEY = "a34981689f7b66c949c0d943caae0ce5"
GEOCODING_API_URL = "http://api.openweathermap.org/geo/1.0/direct"
RAINFALL_API_URL = "https://archive-api.open-meteo.com/v1/archive"
UNSPLASH_ACCESS_KEY = "gaRvmF8K8y00yq4FSn1CDoaOgn6VmaVczETrIH_Fe_Y"
UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"

# Database Connection
def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='users_db',
        cursorclass=pymysql.cursors.DictCursor  # Use DictCursor here
    )

# Convert City Name to Latitude & Longitude
def get_coordinates(city_name):
    try:
        url = f"{GEOCODING_API_URL}?q={city_name}&limit=1&appid={WEATHER_API_KEY}"
        response = requests.get(url)
        response.raise_for_status()
        location_data = response.json()
        if location_data:
            return location_data[0]["lat"], location_data[0]["lon"]
        return None, None
    except Exception as e:
        print(f"Error fetching coordinates: {e}")
        return None, None

# Fetch Yearly Rainfall Data
def get_rainfall_data(latitude, longitude):
    try:
        url = f"{RAINFALL_API_URL}?latitude={latitude}&longitude={longitude}&start_date=2023-01-01&end_date=2023-12-31&daily=precipitation_sum&timezone=auto"
        response = requests.get(url)
        response.raise_for_status()
        rainfall_json = response.json()
        daily_rainfall = rainfall_json.get("daily", {}).get("precipitation_sum", [])
        if daily_rainfall:
            yearly_rainfall = sum(daily_rainfall)
            return f"{yearly_rainfall:.2f} mm"
        return "Unknown"
    except Exception as e:
        print(f"Error fetching rainfall data: {e}")
        return "Unknown"

# Fetch Crop Image from Unsplash
def get_crop_image(crop_name):
    try:
        params = {
            "query": crop_name,
            "client_id": UNSPLASH_ACCESS_KEY,
            "per_page": 5  # Fetch 5 images per crop
        }
        response = requests.get(UNSPLASH_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if data["results"]:
            return [img["urls"]["regular"] for img in data["results"]]
        return ["/static/default_crop.jpg"]
    except Exception as e:
        print(f"Error fetching images from Unsplash: {e}")
        return ["/static/default_crop.jpg"]

# Save Weather Data into Database
def save_weather_data(user_id, city, temperature, humidity, avg_rainfall, soil_type):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO weather_data (user_id, city, temperature, humidity, rainfall, soil)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, city, temperature, humidity, avg_rainfall, soil_type if soil_type else None))
        conn.commit()
    except pymysql.MySQLError as e:
        print(f"Error inserting data into database: {e}")
    finally:
        cursor.close()
        conn.close()

# Save Suggested Crops into Database
def save_suggested_crops(user_id, crop_name, temperature, humidity, avg_rainfall, soil_type):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO suggestions (user_id, crop_name, temperature, humidity, rainfall, soil_type) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, crop_name, temperature, humidity, avg_rainfall, soil_type)
        )
        conn.commit()
    except pymysql.MySQLError as e:
        print(f"Error inserting suggestions into database: {e}")
    finally:
        cursor.close()
        conn.close()

@app.route("/crop_suggestion", methods=["POST"])
def crop_suggestion():
    if "user_id" not in session:
        flash("Please log in to access crop suggestions.", "warning")
        return redirect(url_for("login"))

    avg_rainfall = request.form.get("avg_rainfall")
    soil_type = request.form.get("soil")

    if not avg_rainfall:
        flash("Please enter a valid average rainfall.", "danger")
        return redirect(url_for("weatherinput"))

    try:
        avg_rainfall = float(avg_rainfall.replace(" mm", ""))  # Convert to float
    except ValueError:
        flash("Invalid rainfall value.", "danger")
        return redirect(url_for("weatherinput"))

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT * FROM crops
        WHERE %s > rainfall_min
    """
    params = [avg_rainfall]

    if soil_type and soil_type.strip():
        query += " AND LOWER(soil_type) LIKE LOWER(%s)"
        params.append(f"%{soil_type}%")  # Partial match for soil type

    cursor.execute(query, tuple(params))
    suitable_crops = cursor.fetchall()

    if suitable_crops:
        user_id = session["user_id"]
        cursor.executemany("""
            INSERT INTO suggestions (user_id, crop_name, temperature, humidity, rainfall, soil_type)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, [(user_id, crop["crop_name"], None, None, avg_rainfall, soil_type) for crop in suitable_crops])
        conn.commit()

    for crop in suitable_crops:
        crop["image_urls"] = get_crop_image(crop["crop_name"])  # Fetch multiple images

    cursor.close()
    conn.close()

    return render_template("crop_suggestion.html", suitable_crops=suitable_crops)

# Weather Input Page
@app.route("/weatherinput", methods=["GET", "POST"])
def weatherinput():
    if "user_id" not in session:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for("login"))

    weather_data = None
    avg_rainfall = "Unknown"
    soil_type = None  

    if request.method == "POST":
        city = request.form.get("city")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        soil_type = request.form.get("soil")  

        if city:
            latitude, longitude = get_coordinates(city)
            if not latitude or not longitude:
                flash("Invalid city name. Please try again.", "danger")
                return render_template("weatherinput.html", weather=None, avg_rainfall=avg_rainfall, soil=soil_type)

        if latitude and longitude:
            url = f"http://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={WEATHER_API_KEY}&units=metric"

            try:
                response = requests.get(url)
                response.raise_for_status()
                weather_json = response.json()

                if weather_json.get("cod") == 200:
                    city_name = weather_json["name"]
                    temperature = weather_json["main"]["temp"]
                    humidity = weather_json["main"]["humidity"]

                    weather_data = {
                        "city": city_name,
                        "temperature": temperature,
                        "description": weather_json["weather"][0]["description"],
                        "humidity": humidity
                    }

                    avg_rainfall = get_rainfall_data(latitude, longitude)

                    save_weather_data(session["user_id"], city_name, temperature, humidity, avg_rainfall, soil_type)

                else:
                    flash("Location not found. Try again.", "danger")

            except requests.exceptions.RequestException as e:
                flash("Error fetching weather data. Try again later.", "danger")
                print(f"Weather API Error: {e}")

    return render_template("weatherinput.html", weather=weather_data, avg_rainfall=avg_rainfall, soil=soil_type)

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if "admin_id" in session:
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE username = %s", (username,))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        if admin:
            stored_password = admin["password"]  # Plain text password from DB
            
            if stored_password == password:  # Directly compare (no hashing)
                session["admin_id"] = admin["id"]
                session["admin_username"] = admin["username"]
                flash("Admin login successful!", "success")
                return redirect(url_for("admin_dashboard"))
            else:
                flash("Incorrect password!", "danger")
        else:
            flash("Admin not found!", "danger")

    return render_template("admin_login.html")

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, email FROM users")
    users = cursor.fetchall()

    cursor.execute("SELECT * FROM crops")
    crops = cursor.fetchall()

    conn.close()
    return render_template('admin_dashboard.html', users=users, crops=crops)

@app.route('/admin_logout')
def admin_logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for('admin_login'))

# Add Crop
@app.route('/add_crop', methods=['POST'])
def add_crop():
    conn = get_db_connection()
    cursor = conn.cursor()

    crop_name = request.form.get('crop_name')
    temp_min = request.form.get('temp_min')
    temp_max = request.form.get('temp_max')
    rainfall_min = request.form.get('rainfall_min')
    rainfall_max = request.form.get('rainfall_max')
    avg_rainfall = request.form.get('avg_rainfall')
    soil_type = request.form.get('soil_type')
    description = request.form.get('description')

    query = """
    INSERT INTO crops (crop_name, temp_min, temp_max, rainfall_min, rainfall_max, avg_rainfall, soil_type, description) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (crop_name, temp_min, temp_max, rainfall_min, rainfall_max, avg_rainfall, soil_type, description))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Crop added successfully!", "success")
    return redirect(url_for('admin_dashboard'))

# Edit Crop
# Edit Crop Route
@app.route('/edit_crop/<int:crop_id>', methods=['POST'])
def edit_crop(crop_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get form data
        crop_data = {
            'crop_name': request.form['crop_name'],
            'temp_min': float(request.form['temp_min']),
            'temp_max': float(request.form['temp_max']),
            'rainfall_min': float(request.form['rainfall_min']),
            'rainfall_max': float(request.form['rainfall_max']),
            'avg_rainfall': float(request.form['avg_rainfall']),
            'soil_type': request.form['soil_type'],
            'description': request.form['description'],
            'crop_id': crop_id
        }

        # Update query
        cursor.execute("""
            UPDATE crops SET
                crop_name = %(crop_name)s,
                temp_min = %(temp_min)s,
                temp_max = %(temp_max)s,
                rainfall_min = %(rainfall_min)s,
                rainfall_max = %(rainfall_max)s,
                avg_rainfall = %(avg_rainfall)s,
                soil_type = %(soil_type)s,
                description = %(description)s
            WHERE crop_id = %(crop_id)s
        """, crop_data)

        conn.commit()
        flash('Crop updated successfully!', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Error updating crop: {str(e)}', 'danger')
    finally:
        if conn:
            cursor.close()
            conn.close()

    return redirect(url_for('admin_dashboard'))

# Delete Crop Route
@app.route('/delete_crop/<int:crop_id>', methods=['POST'])
def delete_crop(crop_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Delete query
        cursor.execute("DELETE FROM crops WHERE crop_id = %s", (crop_id,))
        conn.commit()
        flash('Crop deleted successfully!', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Error deleting crop: {str(e)}', 'danger')
    finally:
        if conn:
            cursor.close()
            conn.close()

    return redirect(url_for('admin_dashboard'))

@app.route("/previous_suggestions")
def previous_suggestions():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    
    db = get_db_connection()
    cursor = db.cursor()

    query = "SELECT * FROM suggestions WHERE user_id = %s ORDER BY suggested_at DESC"
    cursor.execute(query, (user_id,))
    suggestions = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("previous_suggestions.html", suggestions=suggestions)

# Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

# Home Route
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("weatherinput"))
    return redirect(url_for("login"))

# Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("weatherinput"))

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash("Login successful!", "success")
            return redirect(url_for("weatherinput"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html")

# Signup Route
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", 
                           (name, email, hashed_password))
            conn.commit()
            session["user_id"] = cursor.lastrowid
            session["user_name"] = name
            flash("Signup successful!", "success")
            return redirect(url_for("weatherinput"))
        except pymysql.MySQLError as e:
            flash("Email already exists. Try logging in.", "danger")
            return redirect(url_for("signup"))
        finally:
            cursor.close()
            conn.close()

    return render_template("signup.html")

if __name__ == "__main__":
    app.run(debug=True)