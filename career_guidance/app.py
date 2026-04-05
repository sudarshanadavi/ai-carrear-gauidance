from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "career_guidance_secret_key"

DB_FILE = "career_guidance.db"

# Career recommendations based on interests and skills
CAREER_MAP = {
    ("technology", "programming"):     ["Software Engineer", "Data Scientist", "Web Developer"],
    ("technology", "design"):          ["UI/UX Designer", "Front-End Developer", "Product Designer"],
    ("technology", "problem solving"): ["Systems Analyst", "DevOps Engineer", "Cybersecurity Analyst"],
    ("science", "research"):           ["Research Scientist", "Biomedical Engineer", "Data Analyst"],
    ("science", "mathematics"):        ["Statistician", "Actuary", "Quantitative Analyst"],
    ("arts", "creativity"):            ["Graphic Designer", "Content Creator", "Art Director"],
    ("arts", "communication"):         ["Copywriter", "Journalist", "Public Relations Specialist"],
    ("business", "leadership"):        ["Project Manager", "Business Analyst", "Entrepreneur"],
    ("business", "communication"):     ["Marketing Manager", "Sales Executive", "HR Manager"],
    ("healthcare", "helping others"):  ["Doctor", "Nurse", "Counselor"],
    ("healthcare", "research"):        ["Pharmacist", "Medical Researcher", "Clinical Analyst"],
}

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users 
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS career_inputs
             (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                interest TEXT NOT NULL,
                skill TEXT NOT NULL,
                recommended_careers TEXT NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()

def get_careers(interest, skill):
    key = (interest.lower(), skill.lower())
    if key in CAREER_MAP:
        return CAREER_MAP[key]
    matches = []
    for (i, s), careers in CAREER_MAP.items():
        if i == interest.lower() or s == skill.lower():
            matches.extend(careers)
    return list(set(matches)) if matches else ["Career Counselor", "General Consultant", "Educator"]

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        if not username or not password:
            error = "All fields are required."
        else:
            try:
                with get_db() as conn:
                    conn.execute(
                        "INSERT INTO users (username, password) VALUES (?, ?)",
                        (username, password)
                    )
                    conn.commit()
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "Username already exists."
    return render_template("signup.html", error=error)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username = ? AND password = ?",
                (username, password)
            ).fetchone()
        if user:
            session["user"] = username
            session["user_id"] = user["id"]
            return redirect(url_for("guidance"))
        else:
            error = "Invalid username or password."
    return render_template("login.html", error=error)

@app.route("/guidance", methods=["GET", "POST"])
def guidance():
    if "user" not in session:
        return redirect(url_for("login"))

    careers = []
    history = []

    if request.method == "POST":
        interest = request.form.get("interest", "")
        skill = request.form.get("skill", "")
        careers = get_careers(interest, skill)

        # Save input + results to DB
        with get_db() as conn:
            conn.execute(
                "INSERT INTO career_inputs (user_id, interest, skill, recommended_careers) VALUES (?, ?, ?, ?)",
                (session["user_id"], interest, skill, ", ".join(careers))
            )
            conn.commit()

    # Load this user's past searches
    with get_db() as conn:
        history = conn.execute(
            "SELECT interest, skill, recommended_careers, submitted_at FROM career_inputs WHERE user_id = ? ORDER BY submitted_at DESC LIMIT 5",
            (session["user_id"],)
        ).fetchall()

    return render_template("guidance.html", user=session["user"], careers=careers, history=history)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
