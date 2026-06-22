from flask import Flask, request, redirect, render_template, Response, flash
import sqlite3
import csv
from io import StringIO
import matplotlib.pyplot as plt
import os
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

app = Flask(__name__)

app.secret_key = "khata_kitab_v11_secret"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


def get_db():
    return sqlite3.connect("khatakitab.db")


class User(UserMixin):

    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email


@login_manager.user_loader
def load_user(user_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, email
        FROM users
        WHERE id=?
    """, (user_id,))

    row = cur.fetchone()
    conn.close()

    if row:
        return User(row[0], row[1], row[2])

    return None


@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE email=?", (email,))
        existing_user = cur.fetchone()

        if existing_user:
            conn.close()
            flash("Email already registered")
            return redirect("/signup")

        password_hash = generate_password_hash(password)

        cur.execute("""
            INSERT INTO users(name, email, password_hash)
            VALUES (?, ?, ?)
        """, (name, email, password_hash))

        conn.commit()
        user_id = cur.lastrowid
        conn.close()

        user = User(user_id, name, email)
        login_user(user)

        return redirect("/")

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect("/")

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, name, email, password_hash
            FROM users
            WHERE email=?
        """, (email,))

        row = cur.fetchone()
        conn.close()

        if row and check_password_hash(row[3], password):
            user = User(row[0], row[1], row[2])
            login_user(user)
            return redirect("/")

        flash("Invalid email or password")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")


@app.route("/landing")
def landing():

    if current_user.is_authenticated:
        return redirect("/")

    return render_template("landing.html")


def generate_charts(user_id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE transaction_type='Income' AND user_id=?
    """, (user_id,))
    income = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE transaction_type='Expense' AND user_id=?
    """, (user_id,))
    expense = cur.fetchone()[0]

    os.makedirs("static/charts", exist_ok=True)

    plt.figure(figsize=(5, 4))
    plt.bar(["Income", "Expense"], [income, expense])
    plt.title("Income vs Expense")
    plt.tight_layout()
    plt.savefig("static/charts/income_expense.png")
    plt.close()

    cur.execute("""
        SELECT category, SUM(amount)
        FROM transactions
        WHERE transaction_type='Expense' AND user_id=?
        GROUP BY category
    """, (user_id,))

    rows = cur.fetchall()

    if rows:
        labels = [row[0] for row in rows]
        values = [row[1] for row in rows]

        plt.figure(figsize=(6, 6))
        plt.pie(values, labels=labels, autopct="%1.1f%%")
        plt.title("Expense Categories")
        plt.tight_layout()
        plt.savefig("static/charts/category_pie.png")
        plt.close()

    conn.close()


@app.route("/")
@login_required
def home():

    search = request.args.get("search", "")
    user_id = current_user.id

    conn = get_db()
    cur = conn.cursor()

    if search:
        cur.execute("""
            SELECT *
            FROM transactions
            WHERE user_id=?
              AND (
                category LIKE ?
                OR note LIKE ?
                OR transaction_type LIKE ?
              )
            ORDER BY transaction_date DESC, id DESC
        """, (
            user_id,
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))

    else:
        cur.execute("""
            SELECT *
            FROM transactions
            WHERE user_id=?
            ORDER BY transaction_date DESC, id DESC
        """, (user_id,))

    transactions = cur.fetchall()

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE transaction_type='Income' AND user_id=?
    """, (user_id,))
    total_income = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE transaction_type='Expense' AND user_id=?
    """, (user_id,))
    total_expense = cur.fetchone()[0]

    balance = total_income - total_expense

    cur.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE user_id=?
    """, (user_id,))
    transaction_count = cur.fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        transactions=transactions,
        total_income=round(total_income, 2),
        total_expense=round(total_expense, 2),
        balance=round(balance, 2),
        transaction_count=transaction_count,
        search=search
    )


@app.route("/add", methods=["POST"])
@login_required
def add():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO transactions(
            transaction_date,
            transaction_type,
            amount,
            category,
            note,
            user_id
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        request.form["transaction_date"],
        request.form["transaction_type"],
        request.form["amount"],
        request.form["category"],
        request.form["note"],
        current_user.id
    ))

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/delete/<int:id>")
@login_required
def delete(id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM transactions WHERE id=? AND user_id=?",
        (id, current_user.id)
    )

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):

    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":

        cur.execute("""
            UPDATE transactions
            SET transaction_date=?,
                transaction_type=?,
                amount=?,
                category=?,
                note=?
            WHERE id=? AND user_id=?
        """, (
            request.form["transaction_date"],
            request.form["transaction_type"],
            request.form["amount"],
            request.form["category"],
            request.form["note"],
            id,
            current_user.id
        ))

        conn.commit()
        conn.close()

        return redirect("/")

    cur.execute(
        "SELECT * FROM transactions WHERE id=? AND user_id=?",
        (id, current_user.id)
    )

    txn = cur.fetchone()
    conn.close()

    if not txn:
        flash("Transaction not found.")
        return redirect("/")

    return render_template("edit.html", txn=txn)


@app.route("/reports")
@login_required
def reports():

    user_id = current_user.id
    generate_charts(user_id)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE transaction_type='Income' AND user_id=?
    """, (user_id,))
    total_income = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE transaction_type='Expense' AND user_id=?
    """, (user_id,))
    total_expense = cur.fetchone()[0]

    balance = total_income - total_expense

    cur.execute("""
        SELECT COALESCE(MAX(amount), 0)
        FROM transactions
        WHERE transaction_type='Expense' AND user_id=?
    """, (user_id,))
    highest_expense = cur.fetchone()[0]

    cur.execute("""
        SELECT category, SUM(amount) total
        FROM transactions
        WHERE transaction_type='Expense' AND user_id=?
        GROUP BY category
        ORDER BY total DESC
        LIMIT 1
    """, (user_id,))

    top_row = cur.fetchone()
    top_category = top_row[0] if top_row else "No Data"

    cur.execute("""
        SELECT category, ROUND(SUM(amount), 2)
        FROM transactions
        WHERE transaction_type='Expense' AND user_id=?
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """, (user_id,))

    category_data = cur.fetchall()
    conn.close()

    return render_template(
        "reports.html",
        total_income=round(total_income, 2),
        total_expense=round(total_expense, 2),
        balance=round(balance, 2),
        highest_expense=round(highest_expense, 2),
        top_category=top_category,
        category_data=category_data
    )


@app.route("/export")
@login_required
def export_csv():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            transaction_date,
            transaction_type,
            amount,
            category,
            note
        FROM transactions
        WHERE user_id=?
    """, (current_user.id,))

    rows = cur.fetchall()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(["Date", "Type", "Amount", "Category", "Note"])
    writer.writerows(rows)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=khatakitab.csv"
        }
    )


if __name__ == "__main__":
    app.run(debug=True)