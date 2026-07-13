import io
import base64
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# Matplotlib configuration for background servers
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = "super_secret_khata_key"

# ---- Flask-Login Configuration ----
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Mock User Class matching all frontend variables (.name and .email)
class User(UserMixin):
    def __init__(self, id, name, email):
        self.id = id
        self.name = name
        self.email = email

# Global mock user instance for demonstration
MOCK_USER = User(id="1", name="Utkarsh Rathi", email="utkarsh@khata.com")

@login_manager.user_loader
def load_user(user_id):
    # dynamic simulation fallback checks
    if user_id == "1":
        return MOCK_USER
    return None

# ---- Dummy In-Memory Data Storage ----
TRANSACTIONS = [
    {"id": 1, "transaction_date": "2026-06-20", "category": "Food", "note": "Dinner with friends", "amount": 1250.00, "transaction_type": "Expense"},
    {"id": 2, "transaction_date": "2026-06-21", "category": "Salary", "note": "Freelance payout", "amount": 45000.00, "transaction_type": "Income"},
    {"id": 3, "transaction_date": "2026-06-22", "category": "Rent", "note": "June apartment bill", "amount": 12000.00, "transaction_type": "Expense"},
    {"id": 4, "transaction_date": "2026-06-23", "category": "Entertainment", "note": "Movie Night", "amount": 850.00, "transaction_type": "Expense"}
]
BUDGETS = {"Food": 5000.00, "Rent": 15000.00, "Entertainment": 2000.00}
SUBSCRIPTIONS = [
    {"id": 1, "name": "Netflix Premium", "amount": 649.00, "billing_cycle": "Monthly"},
    {"id": 2, "name": "GitHub Copilot", "amount": 850.00, "billing_cycle": "Monthly"}
]

# ---- Core Views Controllers ----

@app.route("/")
@app.route("/dashboard")
def dashboard():
    # FIXED: Agar user logged out hai to automatic standard dashboard shell show karne ke bajaye login bypass check handle karega
    if not current_user.is_authenticated:
        return redirect(url_for('login_page'))

    search_query = request.args.get('search', '').lower()

    filtered_txns = TRANSACTIONS
    if search_query:
        filtered_txns = [t for t in TRANSACTIONS if search_query in t['category'].lower() or search_query in (t['note'] or '').lower()]

    total_income = sum(t['amount'] for t in TRANSACTIONS if t['transaction_type'] == 'Income')
    total_expense = sum(t['amount'] for t in TRANSACTIONS if t['transaction_type'] == 'Expense')
    balance = total_income - total_expense

    savings_rate = 0
    if total_income > 0:
        savings_rate = round(((total_income - total_expense) / total_income) * 100, 1)
        if savings_rate < 0: savings_rate = 0

    budget_alerts = []
    for cat, limit in BUDGETS.items():
        spent = sum(t['amount'] for t in TRANSACTIONS if t['category'] == cat and t['transaction_type'] == 'Expense')
        percentage = round((spent / limit) * 100, 1) if limit > 0 else 0
        budget_alerts.append({
            "category": cat, "spent": spent, "limit": limit, "percentage": percentage,
            "is_danger": percentage >= 100, "is_warning": 80 <= percentage < 100
        })

    return render_template(
        "index.html", search=search_query, transactions=filtered_txns,
        balance=f"{balance:,.2f}", month_income=f"{total_income:,.2f}", total_income=f"{total_income:,.2f}",
        month_expense=f"{total_expense:,.2f}", total_expense=f"{total_expense:,.2f}",
        savings_rate=savings_rate, budget_alerts=budget_alerts, subscriptions=SUBSCRIPTIONS
    )

@app.route("/reports")
@login_required
def reports():
    expenses = [t for t in TRANSACTIONS if t['transaction_type'] == 'Expense']
    total_exp = sum(e['amount'] for e in expenses)

    cat_map = {}
    for e in expenses:
        cat_map[e['category']] = cat_map.get(e['category'], 0) + e['amount']

    category_breakdown = []
    top_category = "None"
    max_spent = 0

    for cat, amt in cat_map.items():
        if amt > max_spent:
            max_spent = amt
            top_category = cat
        percentage = round((amt / total_exp) * 100, 1) if total_exp > 0 else 0
        category_breakdown.append({"category": cat, "total_amount": f"{amt:,.2f}", "percentage": percentage})

    chart_base64 = ""
    if cat_map:
        fig, ax = plt.subplots(figsize=(6, 5))

        labels = [f"{cat}\n({(amt/total_exp)*100:.1f}%)" for cat, amt in cat_map.items()]
        values = list(cat_map.values())
        colors = ['#10b981', '#6366f1', '#f43f5e', '#eab308', '#a855f7']

        wedges, texts = ax.pie(
            values,
            labels=labels,
            startangle=140,
            colors=colors,
            labeldistance=1.15,
            wedgeprops={'linewidth': 3, 'edgecolor': 'white'}
        )

        for text in texts:
            text.set_color('#334155')
            text.set_fontsize(10)
            text.set_weight('bold')

        centre_circle = plt.Circle((0,0), 0.68, fc='white')
        fig.gca().add_artist(centre_circle)

        ax.axis('equal')
        fig.patch.set_facecolor('#ffffff')

        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight', dpi=150)
        img.seek(0)
        chart_base64 = base64.b64encode(img.getvalue()).decode('utf-8')
        plt.close(fig)

    avg_daily_spend = round(total_exp / 30, 2) if total_exp > 0 else 0

    return render_template(
        "reports.html", category_breakdown=category_breakdown,
        avg_daily_spend=f"{avg_daily_spend:,.2f}", top_category=top_category, chart=chart_base64
    )

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")

# ---- Authentication Routes ----

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        # Simulating easy mock verification for password parameters
        login_user(MOCK_USER)
        flash("Welcome back to Khata Kitab ecosystem sync!")
        return redirect(url_for('dashboard'))

    # Simple inline form view falls back gracefully if you don't have login.html created yet
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700&display=swap" rel="stylesheet">
        <title>Login | Khata Kitab</title>
    </head>
    <body class="bg-[#f8fafc] flex items-center justify-center min-h-screen font-['Plus_Jakarta_Sans']">
        <div class="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm w-full max-w-md text-center">
            <h2 class="text-2xl font-bold mb-2 text-slate-800">Welcome to Khata Kitab</h2>
            <p class="text-slate-500 text-sm mb-6">Click below to authenticate into the system environment.</p>
            <form method="POST">
                <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2.5 px-4 rounded-xl transition-all cursor-pointer shadow-md shadow-emerald-600/10">
                    Sign In to Workspace
                </button>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.")
    return redirect(url_for('login_page'))

# ---- Form Actions & Handle Submissions ----

@app.route("/add", methods=["POST"])
@login_required
def add_transaction():
    new_id = len(TRANSACTIONS) + 1
    TRANSACTIONS.append({
        "id": new_id,
        "transaction_date": request.form.get("transaction_date"),
        "category": request.form.get("category"),
        "note": request.form.get("note"),
        "amount": float(request.form.get("amount")),
        "transaction_type": request.form.get("transaction_type")
    })
    flash("Transaction ledger sync operation successful!")
    return redirect(url_for('dashboard'))

@app.route("/delete/<int:txn_id>")
@login_required
def delete_transaction(txn_id):
    global TRANSACTIONS
    TRANSACTIONS = [t for t in TRANSACTIONS if t['id'] != txn_id]
    flash("Transaction deleted successfully!")
    return redirect(url_for('dashboard'))

@app.route("/cancel-subscription/<int:sub_id>")
@login_required
def cancel_subscription(sub_id):
    global SUBSCRIPTIONS
    SUBSCRIPTIONS = [s for s in SUBSCRIPTIONS if s['id'] != sub_id]
    flash("Subscription cancelled successfully.")
    return redirect(url_for('dashboard'))

@app.route("/add-subscription", methods=["POST"])
@login_required
def add_subscription():
    new_id = len(SUBSCRIPTIONS) + 1
    SUBSCRIPTIONS.append({
        "id": new_id,
        "name": request.form.get("name"),
        "amount": float(request.form.get("amount")),
        "billing_cycle": request.form.get("billing_cycle")
    })
    flash("Subscription added successfully!")
    return redirect(url_for('dashboard'))

@app.route("/set-budget", methods=["POST"])
@login_required
def set_budget():
    category = request.form.get("category")
    amount = float(request.form.get("amount"))
    BUDGETS[category] = amount
    flash(f"Budget for {category} set to ₹{amount:,.2f}")
    return redirect(url_for('dashboard'))

@app.route("/update-profile", methods=["POST"])
@login_required
def update_profile():
    new_name = request.form.get("name")
    MOCK_USER.name = new_name
    flash("Personal operational configurations synchronized.")
    return redirect(url_for('profile'))

@app.route("/change-password", methods=["POST"])
@login_required
def change_password():
    new_pwd = request.form.get("new_password")
    confirm_pwd = request.form.get("confirm_password")

    if new_pwd != confirm_pwd:
        flash("Password sync validation mismatch! Please verify inputs.")
        return redirect(url_for('profile'))

    flash("Security parameters successfully updated.")
    return redirect(url_for('profile'))

if __name__ == "__main__":
    app.run(debug=True)