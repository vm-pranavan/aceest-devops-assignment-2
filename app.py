"""
ACEest Fitness & Gym — Flask Web Application
Version 4.0.0 — Converted from Tkinter to Flask for CI/CD deployment
"""

import os
import sqlite3
import random
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, g
)

# ---------------------------------------------------------------------------
# App Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "aceest-fitness-secret-key-2026")

DB_NAME = os.environ.get("DB_NAME", "aceest_fitness.db")

# ---------------------------------------------------------------------------
# Database Helpers
# ---------------------------------------------------------------------------

def get_db():
    """Get a database connection for the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Close database connection at end of request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Initialize database tables and default data."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Users table (role-based login)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'User'
        )
    """)

    # Clients table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            age INTEGER,
            height REAL,
            weight REAL,
            program TEXT,
            calories INTEGER,
            target_weight REAL,
            target_adherence INTEGER,
            membership_status TEXT DEFAULT 'Active',
            membership_end TEXT
        )
    """)

    # Weekly progress
    cur.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            week TEXT NOT NULL,
            adherence INTEGER
        )
    """)

    # Workouts
    cur.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            date TEXT NOT NULL,
            workout_type TEXT,
            duration_min INTEGER,
            notes TEXT
        )
    """)

    # Exercises (per workout)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER,
            name TEXT,
            sets INTEGER,
            reps INTEGER,
            weight REAL
        )
    """)

    # Body metrics
    cur.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            date TEXT NOT NULL,
            weight REAL,
            waist REAL,
            bodyfat REAL
        )
    """)

    # Default admin user
    cur.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", "admin", "Admin")
        )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Program Data
# ---------------------------------------------------------------------------

PROGRAMS = {
    "Fat Loss (FL) - 3 day": {
        "factor": 22,
        "desc": "3-day full-body fat loss program",
        "workout": (
            "Mon: Back Squat 5x5 + Core\n"
            "Wed: Bench Press + 21-15-9\n"
            "Fri: Zone 2 Cardio 30min"
        ),
        "diet": (
            "Breakfast: Egg Whites + Oats\n"
            "Lunch: Grilled Chicken + Brown Rice\n"
            "Dinner: Fish Curry + Millet Roti\n"
            "Target: ~2000 kcal"
        ),
    },
    "Fat Loss (FL) - 5 day": {
        "factor": 24,
        "desc": "5-day split, higher volume fat loss",
        "workout": (
            "Mon: Back Squat 5x5 + Core\n"
            "Tue: EMOM 20min Assault Bike\n"
            "Wed: Bench Press + 21-15-9\n"
            "Thu: Deadlift + Box Jumps\n"
            "Fri: Zone 2 Cardio 30min"
        ),
        "diet": (
            "Breakfast: Egg Whites + Oats\n"
            "Lunch: Grilled Chicken + Brown Rice\n"
            "Dinner: Fish Curry + Millet Roti\n"
            "Target: ~2000 kcal"
        ),
    },
    "Muscle Gain (MG) - PPL": {
        "factor": 35,
        "desc": "Push/Pull/Legs hypertrophy split",
        "workout": (
            "Mon: Squat 5x5\n"
            "Tue: Bench 5x5\n"
            "Wed: Deadlift 4x6\n"
            "Thu: Front Squat 4x8\n"
            "Fri: Incline Press 4x10\n"
            "Sat: Barbell Rows 4x10"
        ),
        "diet": (
            "Breakfast: Eggs + Peanut Butter Oats\n"
            "Lunch: Chicken Biryani\n"
            "Dinner: Mutton Curry + Rice\n"
            "Target: ~3200 kcal"
        ),
    },
    "Beginner (BG)": {
        "factor": 26,
        "desc": "3-day simple beginner full-body program",
        "workout": (
            "Full Body Circuit:\n"
            "- Air Squats\n"
            "- Ring Rows\n"
            "- Push-ups\n"
            "Focus: Technique & Consistency"
        ),
        "diet": (
            "Balanced Tamil Meals\n"
            "Idli / Dosa / Rice + Dal\n"
            "Protein Target: 120g/day"
        ),
    },
}

EXERCISE_POOLS = {
    "Strength": [
        "Squat", "Deadlift", "Bench Press",
        "Overhead Press", "Pull-Up", "Barbell Row",
    ],
    "Hypertrophy": [
        "Leg Press", "Incline Dumbbell Press", "Lat Pulldown",
        "Lateral Raise", "Bicep Curl", "Tricep Extension",
    ],
    "Conditioning": [
        "Running", "Cycling", "Rowing",
        "Burpees", "Jump Rope", "Kettlebell Swings",
    ],
    "Full Body": [
        "Push-Up", "Pull-Up", "Lunge",
        "Plank", "Dumbbell Row", "Dumbbell Press",
    ],
}

# ---------------------------------------------------------------------------
# Auth Decorator
# ---------------------------------------------------------------------------

def login_required(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def calculate_bmi(weight_kg, height_cm):
    """Calculate BMI and return value with category and risk."""
    if height_cm <= 0 or weight_kg <= 0:
        return None, "Invalid", "Invalid input"
    h_m = height_cm / 100.0
    bmi = round(weight_kg / (h_m * h_m), 1)

    if bmi < 18.5:
        category = "Underweight"
        risk = "Potential nutrient deficiency, low energy."
    elif bmi < 25:
        category = "Normal"
        risk = "Low risk if active and strong."
    elif bmi < 30:
        category = "Overweight"
        risk = "Moderate risk; focus on adherence and progressive activity."
    else:
        category = "Obese"
        risk = "Higher risk; prioritize fat loss, consistency, and supervision."

    return bmi, category, risk


def calculate_calories(weight_kg, program_name):
    """Calculate daily calorie target based on weight and program."""
    program = PROGRAMS.get(program_name, {})
    factor = program.get("factor", 25)
    if weight_kg and weight_kg > 0:
        return int(weight_kg * factor)
    return None


def generate_ai_program(program_name, experience_level):
    """Generate an AI-style workout program."""
    focus = "Full Body"
    if "Fat Loss" in program_name:
        focus = "Conditioning"
    elif "Muscle Gain" in program_name:
        focus = "Hypertrophy"

    if experience_level == "beginner":
        sets_range, reps_range, days = (2, 3), (8, 12), 3
    elif experience_level == "intermediate":
        sets_range, reps_range, days = (3, 4), (8, 15), 4
    else:
        sets_range, reps_range, days = (4, 5), (6, 15), 5

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][:days]
    exercises = EXERCISE_POOLS.get(focus, EXERCISE_POOLS["Full Body"])

    program = []
    for day in day_names:
        selected = random.sample(exercises, k=min(3 if days < 4 else 4, len(exercises)))
        for ex in selected:
            program.append({
                "day": day,
                "exercise": ex,
                "sets": random.randint(*sets_range),
                "reps": random.randint(*reps_range),
            })

    return program


# ---------------------------------------------------------------------------
# Routes — Health Check
# ---------------------------------------------------------------------------

@app.route("/api/health")
def health_check():
    """Health check endpoint for Kubernetes probes."""
    return jsonify({"status": "healthy", "version": "4.0.0", "app": "ACEest Fitness"})


# ---------------------------------------------------------------------------
# Routes — Authentication
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    """User login page."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        db = get_db()
        user = db.execute(
            "SELECT id, username, role FROM users WHERE username = ? AND password = ?",
            (username, password)
        ).fetchone()

        if user:
            session["user"] = user["username"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials. Try admin / admin", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """User logout."""
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Routes — Dashboard
# ---------------------------------------------------------------------------

@app.route("/")
@login_required
def dashboard():
    """Main dashboard showing summary stats."""
    db = get_db()
    total_clients = db.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    active_clients = db.execute(
        "SELECT COUNT(*) FROM clients WHERE membership_status = 'Active'"
    ).fetchone()[0]
    total_workouts = db.execute("SELECT COUNT(*) FROM workouts").fetchone()[0]

    recent_clients = db.execute(
        "SELECT name, program, membership_status FROM clients ORDER BY id DESC LIMIT 5"
    ).fetchall()

    return render_template(
        "dashboard.html",
        total_clients=total_clients,
        active_clients=active_clients,
        total_workouts=total_workouts,
        recent_clients=recent_clients,
    )


# ---------------------------------------------------------------------------
# Routes — Clients
# ---------------------------------------------------------------------------

@app.route("/clients")
@login_required
def clients():
    """List all clients."""
    db = get_db()
    all_clients = db.execute(
        "SELECT * FROM clients ORDER BY name"
    ).fetchall()
    return render_template("clients.html", clients=all_clients, programs=PROGRAMS)


@app.route("/clients/add", methods=["POST"])
@login_required
def add_client():
    """Add a new client."""
    name = request.form.get("name", "").strip()
    age = request.form.get("age", type=int)
    height = request.form.get("height", type=float)
    weight = request.form.get("weight", type=float)
    program = request.form.get("program", "")

    if not name:
        flash("Client name is required.", "danger")
        return redirect(url_for("clients"))

    calories = calculate_calories(weight, program)

    db = get_db()
    try:
        db.execute(
            """INSERT INTO clients (name, age, height, weight, program, calories, membership_status)
               VALUES (?, ?, ?, ?, ?, ?, 'Active')""",
            (name, age, height, weight, program, calories)
        )
        db.commit()
        flash(f"Client '{name}' added successfully.", "success")
    except sqlite3.IntegrityError:
        flash(f"Client '{name}' already exists.", "danger")

    return redirect(url_for("clients"))


@app.route("/client/<name>")
@login_required
def client_detail(name):
    """View client details."""
    db = get_db()
    client = db.execute("SELECT * FROM clients WHERE name = ?", (name,)).fetchone()
    if not client:
        flash("Client not found.", "danger")
        return redirect(url_for("clients"))

    # Get progress data
    progress = db.execute(
        "SELECT week, adherence FROM progress WHERE client_name = ? ORDER BY id",
        (name,)
    ).fetchall()

    # Get workouts
    workouts = db.execute(
        "SELECT date, workout_type, duration_min, notes FROM workouts WHERE client_name = ? ORDER BY date DESC",
        (name,)
    ).fetchall()

    # Get metrics
    metrics = db.execute(
        "SELECT date, weight, waist, bodyfat FROM metrics WHERE client_name = ? ORDER BY date DESC",
        (name,)
    ).fetchall()

    # Calculate BMI
    bmi_data = None
    if client["height"] and client["weight"]:
        bmi, category, risk = calculate_bmi(client["weight"], client["height"])
        bmi_data = {"bmi": bmi, "category": category, "risk": risk}

    # Average adherence
    avg_result = db.execute(
        "SELECT AVG(adherence) FROM progress WHERE client_name = ?", (name,)
    ).fetchone()
    avg_adherence = round(avg_result[0], 1) if avg_result[0] else 0

    return render_template(
        "client_detail.html",
        client=client,
        progress=progress,
        workouts=workouts,
        metrics=metrics,
        bmi_data=bmi_data,
        avg_adherence=avg_adherence,
        programs=PROGRAMS,
    )


@app.route("/client/<name>/progress", methods=["POST"])
@login_required
def add_progress(name):
    """Log weekly adherence."""
    adherence = request.form.get("adherence", type=int, default=0)
    week = datetime.now().strftime("Week %U - %Y")

    db = get_db()
    db.execute(
        "INSERT INTO progress (client_name, week, adherence) VALUES (?, ?, ?)",
        (name, week, adherence)
    )
    db.commit()
    flash(f"Progress logged for {name}: {adherence}%", "success")
    return redirect(url_for("client_detail", name=name))


@app.route("/client/<name>/metric", methods=["POST"])
@login_required
def add_metric(name):
    """Log body metrics."""
    m_date = request.form.get("date", date.today().isoformat())
    weight = request.form.get("weight", type=float)
    waist = request.form.get("waist", type=float)
    bodyfat = request.form.get("bodyfat", type=float)

    db = get_db()
    db.execute(
        "INSERT INTO metrics (client_name, date, weight, waist, bodyfat) VALUES (?, ?, ?, ?, ?)",
        (name, m_date, weight, waist, bodyfat)
    )
    db.commit()
    flash(f"Metrics logged for {name}", "success")
    return redirect(url_for("client_detail", name=name))


# ---------------------------------------------------------------------------
# Routes — Workouts
# ---------------------------------------------------------------------------

@app.route("/workouts")
@login_required
def workouts():
    """View all workouts."""
    db = get_db()
    all_workouts = db.execute(
        "SELECT * FROM workouts ORDER BY date DESC"
    ).fetchall()
    clients_list = db.execute("SELECT name FROM clients ORDER BY name").fetchall()
    return render_template("workouts.html", workouts=all_workouts, clients=clients_list)


@app.route("/workouts/add", methods=["POST"])
@login_required
def add_workout():
    """Log a new workout."""
    client_name = request.form.get("client_name", "").strip()
    w_date = request.form.get("date", date.today().isoformat())
    workout_type = request.form.get("workout_type", "")
    duration = request.form.get("duration", type=int, default=60)
    notes = request.form.get("notes", "")

    if not client_name:
        flash("Select a client.", "danger")
        return redirect(url_for("workouts"))

    db = get_db()
    db.execute(
        "INSERT INTO workouts (client_name, date, workout_type, duration_min, notes) VALUES (?, ?, ?, ?, ?)",
        (client_name, w_date, workout_type, duration, notes)
    )
    db.commit()
    flash(f"Workout logged for {client_name}", "success")
    return redirect(url_for("workouts"))


# ---------------------------------------------------------------------------
# Routes — Programs
# ---------------------------------------------------------------------------

@app.route("/programs")
@login_required
def programs():
    """View all fitness programs."""
    return render_template("programs.html", programs=PROGRAMS)


@app.route("/programs/generate", methods=["POST"])
@login_required
def generate_program():
    """Generate AI workout program."""
    client_name = request.form.get("client_name", "").strip()
    experience = request.form.get("experience", "beginner").lower()

    if experience not in ("beginner", "intermediate", "advanced"):
        flash("Invalid experience level.", "danger")
        return redirect(url_for("programs"))

    db = get_db()
    client = db.execute("SELECT program FROM clients WHERE name = ?", (client_name,)).fetchone()

    program_name = client["program"] if client and client["program"] else "Beginner (BG)"
    generated = generate_ai_program(program_name, experience)

    return render_template(
        "programs.html",
        programs=PROGRAMS,
        generated_program=generated,
        generated_for=client_name,
        experience=experience,
    )


# ---------------------------------------------------------------------------
# Routes — BMI Calculator
# ---------------------------------------------------------------------------

@app.route("/bmi", methods=["GET", "POST"])
@login_required
def bmi():
    """BMI calculator page."""
    result = None
    if request.method == "POST":
        weight = request.form.get("weight", type=float, default=0)
        height = request.form.get("height", type=float, default=0)
        bmi_val, category, risk = calculate_bmi(weight, height)
        result = {"bmi": bmi_val, "category": category, "risk": risk,
                  "weight": weight, "height": height}

    return render_template("bmi.html", result=result)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    debug_mode = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
