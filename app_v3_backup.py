from flask import Flask, request, redirect
import sqlite3

app = Flask(__name__)

# =========================
# Database Setup
# =========================

def init_db():
    conn = sqlite3.connect("khatakitab.db")
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL,
        category TEXT,
        note TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# Home Page
# =========================

@app.route("/")
def home():

    conn = sqlite3.connect("khatakitab.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM expenses ORDER BY id DESC")
    expenses = cur.fetchall()

    cur.execute("SELECT SUM(amount) FROM expenses")
    total = cur.fetchone()[0]

    conn.close()

    if total is None:
        total = 0

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Khata Kitab</title>

        <style>

        body {{
            font-family: Arial, sans-serif;
            background: #f4f6f9;
            padding: 30px;
        }}

        .container {{
            max-width: 900px;
            margin: auto;
        }}

        .card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0px 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}

        h1 {{
            color: #2563eb;
        }}

        input, select {{
            padding: 10px;
            margin: 5px;
        }}

        button {{
            background: #2563eb;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 6px;
            cursor: pointer;
        }}

        .expense {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}

        .delete {{
            color: red;
            text-decoration: none;
            margin-left: 15px;
        }}

        </style>

    </head>

    <body>

    <div class="container">

        <div class="card">
            <h1>Khata Kitab</h1>
            <h2>Total Spent: Rs. {total:.2f}</h2>
        </div>

        <div class="card">

            <h3>Add Expense</h3>

            <form action="/add" method="post">

                <input
                    type="number"
                    step="0.01"
                    name="amount"
                    placeholder="Amount"
                    required>

                <select name="category">
                    <option>Food</option>
                    <option>Travel</option>
                    <option>Shopping</option>
                    <option>Bills</option>
                    <option>Other</option>
                </select>

                <input
                    type="text"
                    name="note"
                    placeholder="Note">

                <button type="submit">
                    Add Expense
                </button>

            </form>

        </div>

        <div class="card">
            <h3>Expense History</h3>
    """

    for e in expenses:
        html += f"""
            <div class="expense">

                <strong>Rs. {e[1]}</strong>
                |
                {e[2]}
                |
                {e[3]}

                <a
                    class="delete"
                    href="/delete/{e[0]}"
                    onclick="return confirm('Delete this expense?')">
                    Delete
                </a>

            </div>
        """

    html += """
        </div>
    </div>

    </body>
    </html>
    """

    return html

# =========================
# Add Expense
# =========================

@app.route("/add", methods=["POST"])
def add():

    amount = request.form["amount"]
    category = request.form["category"]
    note = request.form["note"]

    conn = sqlite3.connect("khatakitab.db")
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO expenses(amount, category, note) VALUES (?, ?, ?)",
        (amount, category, note)
    )

    conn.commit()
    conn.close()

    return redirect("/")

# =========================
# Delete Expense
# =========================

@app.route("/delete/<int:id>")
def delete(id):

    conn = sqlite3.connect("khatakitab.db")
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM expenses WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/")

# =========================
# Start App
# =========================

if __name__ == "__main__":
    app.run(debug=True)