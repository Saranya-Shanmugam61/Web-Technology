from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import uuid # For generating unique user IDs
from datetime import date, datetime, timedelta # Import date, datetime, timedelta for logging and date calculations

# --- Flask Application Setup ---
app = Flask(__name__)

# IMPORTANT: In a production environment, store this in environment variables!
app.config['SECRET_KEY'] = 'your_super_secret_and_unique_key_here_replace_this' # <--- CHANGE THIS!

# --- MySQL Database Configuration ---
# IMPORTANT: Replace these with your actual MySQL credentials
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',       # Your MySQL username
    'password': '', # <--- YOUR MYSQL PASSWORD
    'database': 'nutrisync_database' # The database name for NutriSync
}

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'home' # Redirect to home if not logged in

# --- Context Processor for Global Template Variables ---
# This makes 'current_year' available in ALL your Jinja2 templates
@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}


# --- Database Connection Helper ---
def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database']
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None

def get_db_connection_no_db():
    """Establishes a connection to MySQL without specifying a database,
    used for creating the database if it doesn't exist."""
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        return conn
    except mysql.connector.Error as err:
            print(f"Error connecting to MySQL server: {err}")
            return None

# --- Database Initialization (Create DB and Table if not exist) ---
def init_db():
    """Initializes the database: creates the database and users table if they don't exist."""
    # First, connect without specifying a database to create it if needed
    conn = get_db_connection_no_db()
    if conn:
        cursor = conn.cursor()
        try:
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
            print(f"Database '{DB_CONFIG['database']}' ensured to exist.")
            conn.commit()
        except mysql.connector.Error as err:
            print(f"Error creating database: {err}")
        finally:
            cursor.close()
            conn.close()

    # Now, connect to the specific database to create the table
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Create users table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(255) PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL
                )
            """)
            print("Table 'users' ensured to exist.")

            # Create food_entries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS food_entries (
                    id VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    meal_time VARCHAR(50) NOT NULL,
                    diet_goal VARCHAR(50),
                    food_item TEXT NOT NULL,
                    calories INT,
                    proteins DECIMAL(10,2),
                    carbs DECIMAL(10,2),
                    fats DECIMAL(10,2),
                    entry_date DATE NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            print("Table 'food_entries' ensured to exist.")

            # Create workout_entries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workout_entries (
                    id VARCHAR(255) PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    workout_type VARCHAR(100) NOT NULL,
                    duration_minutes INT,
                    calories_burned INT,
                    entry_date DATE NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            print("Table 'workout_entries' ensured to exist.")

            conn.commit()
        except mysql.connector.Error as err:
            print(f"Error creating tables: {err}")
        finally:
            cursor.close()
            conn.close()

# --- User Management (Now using MySQL) ---
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    def get_id(self):
        return str(self.id)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    """Loads a user from the database given their ID."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True) # Return rows as dictionaries
        try:
            cursor.execute("SELECT id, username, password_hash FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                return User(user_data['id'], user_data['username'], user_data['password_hash'])
        except mysql.connector.Error as err:
            print(f"Error loading user: {err}")
        finally:
            cursor.close()
            conn.close()
    return None

# --- Routes ---

@app.route('/')
@app.route('/home')
def home():
    # Pass a variable to the template to indicate if a modal should be shown
    show_login_modal = request.args.get('showLoginModal', 'false').lower() == 'true'
    show_register_modal = request.args.get('showRegisterModal', 'false').lower() == 'true'
    return render_template('index.html',
                           show_login_modal=show_login_modal,
                           show_register_modal=show_register_modal)

@app.route('/login', methods=['POST'])
def login_submit():
    username = request.form.get('username')
    password = request.form.get('password')

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (username,))
            user_data = cursor.fetchone()
            if user_data:
                user = User(user_data['id'], user_data['username'], user_data['password_hash'])
                if user.check_password(password):
                    login_user(user)
                    flash('Logged in successfully!', 'success')
                    return redirect(url_for('home'))
                else:
                    flash('Invalid username or password.', 'danger')
            else:
                flash('Invalid username or password.', 'danger')
        except mysql.connector.Error as err:
            print(f"Error during login: {err}")
            flash('An error occurred during login. Please try again.', 'danger')
        finally:
            cursor.close()
            conn.close()

    # Redirect back to home with a flag to show the login modal if login failed
    return redirect(url_for('home', showLoginModal='true'))

@app.route('/register', methods=['POST'])
def register_submit():
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash('Username and password are required.', 'danger')
        return redirect(url_for('home', showRegisterModal='true'))

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Check if username already exists
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                flash('Username already exists. Please choose a different one.', 'danger')
                return redirect(url_for('home', showRegisterModal='true'))

            user_id = str(uuid.uuid4()) # Generate a unique ID for the user
            password_hash = generate_password_hash(password)

            cursor.execute(
                "INSERT INTO users (id, username, password_hash) VALUES (%s, %s, %s)",
                (user_id, username, password_hash)
            )
            conn.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('home', showLoginModal='true')) # Show login modal after successful registration
        except mysql.connector.Error as err:
            print(f"Error during registration: {err}")
            flash('An error occurred during registration. Please try again.', 'danger')
        finally:
            cursor.close()
            conn.close()
    else:
        flash('Database connection error. Please try again later.', 'danger')

    return redirect(url_for('home', showRegisterModal='true')) # Fallback redirect

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/notifications')
@login_required
def notifications():
    # Example notifications (you'd fetch these from a DB in a real app)
    notifications_list = [
        {"id": 1, "message": "Your meal plan for today is ready!", "read": False},
        {"id": 2, "message": "You've reached 80% of your protein goal.", "read": True},
        {"id": 3, "message": "New exercise routine added to your dashboard.", "read": False}
    ]
    return render_template('notifications.html', notifications=notifications_list)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    # This route would typically handle a contact form submission or display contact info
    return render_template('contact.html')

@app.route('/progress')
@login_required
def progress():
    # This will now be a dashboard page linking to the specific progress sections
    return render_template('progress.html')

@app.route('/food_schedule', methods=['GET'])
@login_required
def food_schedule():
    user_id = current_user.id
    selected_date_str = request.args.get('date', date.today().isoformat())
    selected_date = date.fromisoformat(selected_date_str)

    conn = get_db_connection()
    food_entries = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT meal_time, diet_goal, food_item, calories, proteins, carbs, fats
                FROM food_entries
                WHERE user_id = %s AND entry_date = %s
                ORDER BY timestamp ASC
            """, (user_id, selected_date))
            food_entries = cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Error fetching food entries: {err}")
            flash('Error loading your food schedule.', 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('food_schedule.html',
                           food_entries=food_entries,
                           selected_date=selected_date.isoformat())

@app.route('/add_food_entry', methods=['POST'])
@login_required
def add_food_entry():
    user_id = current_user.id
    meal_time = request.form.get('meal_time')
    diet_goal = request.form.get('diet_goal')
    food_item = request.form.get('food_item')
    calories = request.form.get('calories')
    proteins = request.form.get('proteins')
    carbs = request.form.get('carbs')
    fats = request.form.get('fats')
    entry_date_str = request.form.get('entry_date')

    if not all([meal_time, food_item, entry_date_str]):
        flash('Missing required food entry fields.', 'danger')
        return redirect(url_for('food_schedule'))

    try:
        calories = int(calories) if calories else 0
        proteins = float(proteins) if proteins else 0.0
        carbs = float(carbs) if carbs else 0.0
        fats = float(fats) if fats else 0.0
        entry_date = date.fromisoformat(entry_date_str)
    except ValueError:
        flash('Invalid numerical or date input for food entry.', 'danger')
        return redirect(url_for('food_schedule'))

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            entry_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO food_entries (id, user_id, meal_time, diet_goal, food_item, calories, proteins, carbs, fats, entry_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (entry_id, user_id, meal_time, diet_goal, food_item, calories, proteins, carbs, fats, entry_date))
            conn.commit()
            flash('Food entry added successfully!', 'success')
        except mysql.connector.Error as err:
            print(f"Error adding food entry: {err}")
            flash('Failed to add food entry. Please try again.', 'danger')
        finally:
            cursor.close()
            conn.close()
    else:
        flash('Database connection error. Please try again later.', 'danger')

    return redirect(url_for('food_schedule', date=entry_date.isoformat()))

@app.route('/exercise_log', methods=['GET'])
@login_required
def exercise_log():
    user_id = current_user.id
    selected_date_str = request.args.get('date', date.today().isoformat())
    selected_date = date.fromisoformat(selected_date_str)

    conn = get_db_connection()
    workout_entries = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT workout_type, duration_minutes, calories_burned
                FROM workout_entries
                WHERE user_id = %s AND entry_date = %s
                ORDER BY timestamp ASC
            """, (user_id, selected_date))
            workout_entries = cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Error fetching workout entries: {err}")
            flash('Error loading your exercise log.', 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('exercise_log.html',
                           workout_entries=workout_entries,
                           selected_date=selected_date.isoformat())

@app.route('/add_workout_entry', methods=['POST'])
@login_required
def add_workout_entry():
    user_id = current_user.id
    workout_type = request.form.get('workout_type')
    duration_minutes = request.form.get('duration_minutes')
    calories_burned = request.form.get('calories_burned')
    entry_date_str = request.form.get('entry_date')

    if not all([workout_type, duration_minutes, calories_burned, entry_date_str]):
        flash('Missing required workout entry fields.', 'danger')
        return redirect(url_for('exercise_log'))

    try:
        duration_minutes = int(duration_minutes)
        calories_burned = int(calories_burned)
        entry_date = date.fromisoformat(entry_date_str)
    except ValueError:
        flash('Invalid numerical or date input for workout entry.', 'danger')
        return redirect(url_for('exercise_log'))

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            entry_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO workout_entries (id, user_id, workout_type, duration_minutes, calories_burned, entry_date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (entry_id, user_id, workout_type, duration_minutes, calories_burned, entry_date))
            conn.commit()
            flash('Workout entry added successfully!', 'success')
        except mysql.connector.Error as err:
            print(f"Error adding workout entry: {err}")
            flash('Failed to add workout entry. Please try again.', 'danger')
        finally:
            cursor.close()
            conn.close()
    else:
        flash('Database connection error. Please try again later.', 'danger')

    return redirect(url_for('exercise_log', date=entry_date.isoformat()))


@app.route('/nutrient_snapshot', methods=['GET'])
@login_required
def nutrient_snapshot():
    user_id = current_user.id
    selected_date_str = request.args.get('date', date.today().isoformat())
    selected_date = date.fromisoformat(selected_date_str)

    # Calculate previous and next dates for navigation
    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)

    conn = get_db_connection()
    food_entries = []
    workout_entries = []
    nutrient_summary = {
        'total_calories': 0,
        'total_proteins': 0.0,
        'total_carbs': 0.0,
        'total_fats': 0.0
    }
    total_calories_burned_from_workouts = 0

    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Fetch food entries for the selected date
            cursor.execute("""
                SELECT meal_time, diet_goal, food_item, calories, proteins, carbs, fats
                FROM food_entries
                WHERE user_id = %s AND entry_date = %s
                ORDER BY timestamp ASC
            """, (user_id, selected_date))
            food_entries = cursor.fetchall()

            # Fetch workout entries for the selected date
            cursor.execute("""
                SELECT workout_type, duration_minutes, calories_burned
                FROM workout_entries
                WHERE user_id = %s AND entry_date = %s
                ORDER BY timestamp ASC
            """, (user_id, selected_date))
            workout_entries = cursor.fetchall()

            # Calculate nutrient summary for the selected date
            for entry in food_entries:
                nutrient_summary['total_calories'] += (entry['calories'] if entry['calories'] else 0)
                nutrient_summary['total_proteins'] += (entry['proteins'] if entry['proteins'] else 0.0)
                nutrient_summary['total_carbs'] += (entry['carbs'] if entry['carbs'] else 0.0)
                nutrient_summary['total_fats'] += (entry['fats'] if entry['fats'] else 0.0)

            for workout in workout_entries:
                total_calories_burned_from_workouts += (workout['calories_burned'] if workout['calories_burned'] else 0)

        except mysql.connector.Error as err:
            print(f"Error fetching nutrient snapshot data: {err}")
            flash('Error loading your nutrient snapshot.', 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('nutrient_snapshot.html',
                           food_entries=food_entries,
                           workout_entries=workout_entries,
                           nutrient_summary=nutrient_summary,
                           total_calories_burned_from_workouts=total_calories_burned_from_workouts,
                           selected_date=selected_date.isoformat(),
                           prev_date=prev_date.isoformat(),
                           next_date=next_date.isoformat())

@app.route('/detailed_report')
@login_required
def detailed_report():
    # This page could show charts (e.g., weekly calorie trend, macro distribution)
    # For now, it's a simple placeholder.
    return render_template('detailed_report.html')

@app.route('/suggest')
@login_required
def suggest():
    # Hardcoded suggestions for now.
    # In a real app, this would be dynamic based on user goals, past entries, etc.
    food_suggestions = [
        {
            "name": "Quinoa Salad with Grilled Chicken",
            "description": "A high-protein, fiber-rich meal. Cooked quinoa, mixed greens, grilled chicken breast, cherry tomatoes, cucumber, and a light lemon-herb dressing.",
            "calories": "450-550 kcal",
            "macros": "Protein: 40g, Carbs: 50g, Fats: 15g"
        },
        {
            "name": "Lentil Soup with Whole Wheat Bread",
            "description": "Hearty and nutritious, packed with plant-based protein and fiber. Serve with a slice of whole wheat bread.",
            "calories": "350-450 kcal",
            "macros": "Protein: 25g, Carbs: 60g, Fats: 8g"
        },
        {
            "name": "Salmon with Roasted Asparagus & Sweet Potato",
            "description": "Rich in Omega-3 fatty acids and complex carbohydrates. Baked salmon fillet, roasted asparagus, and a medium sweet potato.",
            "calories": "500-600 kcal",
            "macros": "Protein: 45g, Carbs: 55g, Fats: 20g"
        },
        {
            "name": "Greek Yogurt with Berries and Nuts",
            "description": "A quick and easy snack or breakfast, high in protein. Plain Greek yogurt topped with mixed berries and a handful of almonds.",
            "calories": "200-300 kcal",
            "macros": "Protein: 20g, Carbs: 30g, Fats: 10g"
        }
    ]

    exercise_suggestions = [
        {
            "name": "Full Body Strength Training (30-45 min)",
            "description": "Compound exercises like squats, deadlifts (or Romanian deadlifts), push-ups, rows, and overhead press. Aim for 3 sets of 8-12 reps.",
            "focus": "Strength, Muscle Growth",
            "calories_burned": "300-500 kcal"
        },
        {
            "name": "HIIT (High-Intensity Interval Training) (20-30 min)",
            "description": "Short bursts of intense exercise followed by brief recovery periods. Examples: Burpees, jumping jacks, high knees, mountain climbers. Work for 45s, rest for 15s, repeat 15-20 times.",
            "focus": "Cardio, Endurance, Fat Loss",
            "calories_burned": "250-400 kcal"
        },
        {
            "name": "Yoga for Flexibility & Core (45-60 min)",
            "description": "Focus on holding poses to improve flexibility, balance, and core strength. Good for recovery and mental well-being.",
            "focus": "Flexibility, Core Strength, Mind-Body",
            "calories_burned": "150-250 kcal"
        },
        {
            "name": "Brisk Walk/Light Jog (30-60 min)",
            "description": "Simple and effective for cardiovascular health. Maintain a pace where you can talk but are slightly breathless.",
            "focus": "Cardio, General Health",
            "calories_burned": "200-400 kcal"
        }
    ]

    return render_template('suggest.html',
                           food_suggestions=food_suggestions,
                           exercise_suggestions=exercise_suggestions)


if __name__ == '__main__':
    # Initialize the database when the application starts
    print("Initializing database...")
    init_db()
    print("Database initialization complete.")
    app.run(debug=True)