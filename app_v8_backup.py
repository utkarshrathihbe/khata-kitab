from flask import Flask, request, redirect, render_template, Response
import sqlite3
import csv
from io import StringIO

app = Flask(__name__)

def get_db():
    return sqlite3.connect("khatakitab.db")

# ======================
# HOME
# ======================

@app.route("/")
def home():

    conn = get_db()
    cur = conn.cursor()

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
        total_income=round(total_income,2),
        total_expense=round(total_expense,2),
        balance=round(balance,2),
        transaction_count=transaction_count
    )

# ======================
# ADD
# ======================

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
    VALUES (?,?,?,?,?)
    """,(
        request.form["transaction_date"],
        request.form["transaction_type"],
        request.form["amount"],
        request.form["category"],
        request.form["note"]
    ))

    conn.commit()
    conn.close()

    return redirect("/")

# ======================
# DELETE
# ======================

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

# ======================
# EDIT
# ======================

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

# ======================
# REPORTS
# ======================

@app.route("/reports")
def reports():

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
        total_income=round(total_income,2),
        total_expense=round(total_expense,2),
        balance=round(balance,2),
        category_data=category_data
    )

# ======================
# EXPORT CSV
# ======================

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

# ======================
# START
# ======================

if __name__ == "__main__":
    app.run(debug=True)