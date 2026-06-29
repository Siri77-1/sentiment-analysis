from flask import Flask, render_template, request, redirect, send_file, session
from textblob import TextBlob
import sqlite3
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------------- DB INIT ----------------
def init_db():
    conn = sqlite3.connect("sentiment.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sentiments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        text TEXT,
        sentiment TEXT,
        polarity REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("sentiment.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/")
        else:
            return "Invalid login"

    return render_template("login.html")


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("sentiment.db")
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            conn.commit()
        except:
            return "User already exists"

        conn.close()
        return redirect("/login")

    return render_template("register.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


# ---------------- HOME ----------------
@app.route("/", methods=["GET", "POST"])
def home():

    if "user" not in session:
        return redirect("/login")

    sentiment = None
    polarity = None

    if request.method == "POST":

        text = request.form["text"]
        polarity = TextBlob(text).sentiment.polarity

        if polarity > 0.1:
            sentiment = "Positive 😊"
        elif polarity < -0.1:
            sentiment = "Negative 😞"
        else:
            sentiment = "Neutral 😐"

        conn = sqlite3.connect("sentiment.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO sentiments (user_id, text, sentiment, polarity)
        VALUES (?, ?, ?, ?)
        """, (session["user"], text, sentiment, polarity))

        conn.commit()
        conn.close()

    search = request.args.get("search", "")

    conn = sqlite3.connect("sentiment.db")
    cursor = conn.cursor()

    if search:
        cursor.execute("""
        SELECT * FROM sentiments
        WHERE text LIKE ?
        ORDER BY id DESC
        """, ('%' + search + '%',))
    else:
        cursor.execute("""
        SELECT * FROM sentiments
        ORDER BY id DESC
        """)

    history = cursor.fetchall()
    conn.close()

    total = len(history)
    positive = sum(1 for r in history if "Positive" in r[3])
    negative = sum(1 for r in history if "Negative" in r[3])
    neutral = sum(1 for r in history if "Neutral" in r[3])
    return render_template(
        "index.html",
        sentiment=sentiment,
        polarity=polarity,
        history=history,
        total=total,
        positive=positive,
        negative=negative,
        neutral=neutral
    )


# ---------------- CSV UPLOAD ----------------
@app.route("/upload", methods=["POST"])
def upload():

    file = request.files["csv_file"]

    path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(path)

    df = pd.read_csv(path)

    conn = sqlite3.connect("sentiment.db")
    cursor = conn.cursor()

    for review in df.iloc[:, 0]:

        polarity = TextBlob(str(review)).sentiment.polarity

        if polarity > 0.1:
            sentiment = "Positive 😊"
        elif polarity < -0.1:
            sentiment = "Negative 😞"
        else:
            sentiment = "Neutral 😐"

        cursor.execute("""
        INSERT INTO sentiments (user_id, text, sentiment, polarity)
        VALUES (?, ?, ?, ?)
        """, (session["user"], str(review), sentiment, polarity))

    conn.commit()
    conn.close()

    return redirect("/")


# ---------------- DOWNLOAD REPORT ----------------
@app.route("/download")
def download():

    conn = sqlite3.connect("sentiment.db")
    df = pd.read_sql_query("SELECT * FROM sentiments", conn)
    conn.close()

    file_path = "report.csv"
    df.to_csv(file_path, index=False)

    return send_file(file_path, as_attachment=True)


# ---------------- CLEAR HISTORY ----------------
@app.route("/clear")
def clear():

    conn = sqlite3.connect("sentiment.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM sentiments")

    conn.commit()
    conn.close()

    return redirect("/")


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)