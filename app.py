from flask import Flask, request, redirect, render_template, Response
import sqlite3
import csv
from io import StringIO
import matplotlib.pyplot as plt
import os

app = Flask(__name__)

def get_db():
    return sqlite3.connect("khatakitab.db")


def generate_charts():

    conn = get_db()
    cur = conn.cursor()

    # Income Total
    cur.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM transactions
        WHERE transaction_type='Income'
    """)
    income = cur.fetchone()[0]

    # Expense Total
    cur.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM transactions
        WHERE transaction_type='Expense'
    """)
    expense = cur.fetchone()[0]

    os.makedirs("static/charts", exist_ok=True)

    # Bar Chart
    plt.figure(figsize=(5,4))
    plt.bar(["Income", "Expense"], [income, expense])
    plt.title("Income vs Expense")
    plt.tight_layout()
    plt.savefig("static/charts/income_expense.png")
    plt.close()

    # Pie Chart
    cur.execute("""
        SELECT category,
               SUM(amount)
        FROM transactions
        WHERE transaction_type='Expense'
        GROUP BY category
    """)

    rows = cur.fetchall()

    if rows:

        labels = [row[0] for row in rows]
        values = [row[1] for row in rows]

        plt.figure(figsize=(6,6))
        plt.pie(values, labels=labels, autopct="%1.1f%%")
        plt.title("Expense Categories")
        plt.tight_layout()
        plt.savefig("static/charts/category_pie.png")
        plt.close()

    conn.close()


@app.route("/")
def home():

    search = request.args.get("search", "")

    conn = get_db()
    cur = conn.cursor()

    if search:

        cur.execute("""
            SELECT *
            FROM transactions
            WHERE category LIKE ?
               OR note LIKE ?
               OR transaction_type LIKE ?
            ORDER BY transaction_date DESC, id DESC
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))

    else:

        cur.execute("""
            SELECT *
            FROM transactions
            ORDER BY transaction_date DESC, id DESC
        """)

    transactions = cur.fetchall()

    cur.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM transactions
        WHERE transaction_type='Income'
    """)
    total_income = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM transactions
        WHERE transaction_type='Expense'
    """)
    total_expense = cur.fetchone()[0]

    balance = total_income - total_expense

    cur.execute("SELECT COUNT(*) FROM transactions")
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
def add():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO transactions(
            transaction_date,
            transaction_type,
            amount,
            category,
            note
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        request.form["transaction_date"],
        request.form["transaction_type"],
        request.form["amount"],
        request.form["category"],
        request.form["note"]
    ))

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/delete/<int:id>")
def delete(id):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM transactions WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
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
            WHERE id=?
        """, (
            request.form["transaction_date"],
            request.form["transaction_type"],
            request.form["amount"],
            request.form["category"],
            request.form["note"],
            id
        ))

        conn.commit()
        conn.close()

        return redirect("/")

    cur.execute(
        "SELECT * FROM transactions WHERE id=?",
        (id,)
    )

    txn = cur.fetchone()

    conn.close()

    return render_template(
        "edit.html",
        txn=txn
    )


@app.route("/reports")
def reports():

    generate_charts()

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM transactions
        WHERE transaction_type='Income'
    """)
    total_income = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM transactions
        WHERE transaction_type='Expense'
    """)
    total_expense = cur.fetchone()[0]

    balance = total_income - total_expense

    cur.execute("""
        SELECT COALESCE(MAX(amount),0)
        FROM transactions
        WHERE transaction_type='Expense'
    """)
    highest_expense = cur.fetchone()[0]

    cur.execute("""
        SELECT category,
               SUM(amount) total
        FROM transactions
        WHERE transaction_type='Expense'
        GROUP BY category
        ORDER BY total DESC
        LIMIT 1
    """)

    top_row = cur.fetchone()

    if top_row:
        top_category = top_row[0]
    else:
        top_category = "No Data"

    cur.execute("""
        SELECT category,
               ROUND(SUM(amount),2)
        FROM transactions
        WHERE transaction_type='Expense'
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """)

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
    """)

    rows = cur.fetchall()

    conn.close()

    output = StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "Date",
        "Type",
        "Amount",
        "Category",
        "Note"
    ])

    writer.writerows(rows)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=khatakitab.csv"
        }
    )


if __name__ == "__main__":
    app.run(debug=True)