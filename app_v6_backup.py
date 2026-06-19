from flask import Flask, request, redirect, render_template
import sqlite3

app = Flask(__name__)

def get_db():
    return sqlite3.connect("khatakitab.db")

@app.route("/")
def home():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT *
    FROM transactions
    ORDER BY transaction_date DESC,id DESC
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

if __name__ == "__main__":
    app.run(debug=True)