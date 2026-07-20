import io
import os
import base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Matplotlib configuration for background servers
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = "super_secret_khata_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///khatakitab.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max upload size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)

# ---- Flask-Login Configuration ----
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_page'

# ---- Database Models ----

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    profile_pic = db.Column(db.String, nullable=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_date = db.Column(db.String)
    category = db.Column(db.String)
    note = db.Column(db.String)
    amount = db.Column(db.Float)
    transaction_type = db.Column(db.String)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String, nullable=False)
    limit_amount = db.Column(db.Float)
    __table_args__ = (db.UniqueConstraint('user_id', 'category', name='uq_user_category'),)

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String)
    amount = db.Column(db.Float)
    billing_cycle = db.Column(db.String)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String, nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String, default="Open")
    created_at = db.Column(db.String)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---- Create tables on first run ----
with app.app_context():
    db.create_all()

# ---- Public Landing Page ----

@app.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template("landing.html")

# ---- Core Views Controllers ----

@app.route("/dashboard")
@login_required
def dashboard():
    search_query = request.args.get('search', '').lower()

    all_txns = Transaction.query.filter_by(user_id=current_user.id).all()
    filtered_txns = all_txns
    if search_query:
        filtered_txns = [t for t in all_txns if search_query in t.category.lower() or search_query in (t.note or '').lower()]

    total_income = sum(t.amount for t in all_txns if t.transaction_type == 'Income')
    total_expense = sum(t.amount for t in all_txns if t.transaction_type == 'Expense')
    balance = total_income - total_expense

    savings_rate = 0
    if total_income > 0:
        savings_rate = round(((total_income - total_expense) / total_income) * 100, 1)
        if savings_rate < 0:
            savings_rate = 0

    budget_alerts = []
    for b in Budget.query.filter_by(user_id=current_user.id).all():
        spent = sum(t.amount for t in all_txns if t.category == b.category and t.transaction_type == 'Expense')
        percentage = round((spent / b.limit_amount) * 100, 1) if b.limit_amount > 0 else 0
        budget_alerts.append({
            "category": b.category, "spent": spent, "limit": b.limit_amount, "percentage": percentage,
            "is_danger": percentage >= 100, "is_warning": 80 <= percentage < 100
        })

    subscriptions = Subscription.query.filter_by(user_id=current_user.id).all()

    return render_template(
        "index.html", search=search_query, transactions=filtered_txns,
        balance=f"{balance:,.2f}", month_income=f"{total_income:,.2f}", total_income=f"{total_income:,.2f}",
        month_expense=f"{total_expense:,.2f}", total_expense=f"{total_expense:,.2f}",
        savings_rate=savings_rate, budget_alerts=budget_alerts, subscriptions=subscriptions
    )

@app.route("/reports")
@login_required
def reports():
    expenses = [t for t in Transaction.query.filter_by(user_id=current_user.id).all() if t.transaction_type == 'Expense']
    total_exp = sum(e.amount for e in expenses)

    cat_map = {}
    for e in expenses:
        cat_map[e.category] = cat_map.get(e.category, 0) + e.amount

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

        centre_circle = plt.Circle((0, 0), 0.68, fc='white')
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

@app.route("/feedback", methods=["GET", "POST"])
@login_required
def feedback_page():
    if request.method == "POST":
        category = request.form.get("category")
        message = (request.form.get("message") or "").strip()

        if not message:
            flash("Please describe your feedback before submitting.")
            return redirect(url_for('feedback_page'))

        entry = Feedback(
            user_id=current_user.id,
            category=category,
            message=message,
            status="Open",
            created_at=datetime.now().strftime("%d %b %Y, %I:%M %p")
        )
        db.session.add(entry)
        db.session.commit()
        flash("Thanks! Your feedback has been submitted.")
        return redirect(url_for('feedback_page'))

    my_feedback = Feedback.query.filter_by(user_id=current_user.id).order_by(Feedback.id.desc()).all()
    return render_template("feedback.html", feedback_list=my_feedback)

# ---- Authentication Routes ----

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Welcome back to Khata Kitab!")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password.")
            return redirect(url_for('login_page'))

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        name = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not name or len(name) < 2:
            flash("Please enter your full name.")
            return redirect(url_for('signup_page'))

        if "@" not in email or "." not in email.split("@")[-1]:
            flash("Please enter a valid email address.")
            return redirect(url_for('signup_page'))

        if len(password) < 6:
            flash("Password must be at least 6 characters long.")
            return redirect(url_for('signup_page'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email already exists.")
            return redirect(url_for('signup_page'))

        new_user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash("Account created successfully! Welcome to Khata Kitab.")
        return redirect(url_for('dashboard'))

    return render_template("signup.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.")
    return redirect(url_for('login_page'))

@app.route("/forgot", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        user = User.query.filter_by(email=email).first()
        # Always show the same message whether or not the email exists,
        # so we don't leak which emails are registered.
        flash("If an account with that email exists, password reset instructions would be sent. (Email sending isn't set up yet.)")
        return redirect(url_for('login_page'))

    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700&display=swap" rel="stylesheet">
        <title>Forgot Password | Khata Kitab</title>
    </head>
    <body class="bg-[#f8fafc] flex items-center justify-center min-h-screen font-['Plus_Jakarta_Sans']">
        <div class="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm w-full max-w-md">
            <h2 class="text-2xl font-bold mb-2 text-slate-800 text-center">Reset Password</h2>
            <p class="text-slate-500 text-sm mb-6 text-center">Enter your email and we will send reset instructions.</p>
            <form method="POST" class="space-y-4">
                <input type="email" name="email" placeholder="name@company.com" required
                       class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-800 focus:outline-none focus:border-emerald-600 focus:bg-white transition-all">
                <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 rounded-xl text-sm transition-all cursor-pointer">
                    Send Reset Instructions
                </button>
            </form>
            <p class="text-center mt-6 text-sm"><a href="/login" class="text-emerald-600 font-semibold hover:underline">Back to Login</a></p>
        </div>
    </body>
    </html>
    '''

# ---- Form Actions & Handle Submissions ----

@app.route("/add", methods=["POST"])
@login_required
def add_transaction():
    txn = Transaction(
        user_id=current_user.id,
        transaction_date=request.form.get("transaction_date"),
        category=request.form.get("category"),
        note=request.form.get("note"),
        amount=float(request.form.get("amount")),
        transaction_type=request.form.get("transaction_type")
    )
    db.session.add(txn)
    db.session.commit()
    flash("Transaction ledger sync operation successful!")
    return redirect(url_for('dashboard'))

@app.route("/export")
@login_required
def export_csv():
    import csv
    txns = Transaction.query.filter_by(user_id=current_user.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Category", "Note", "Amount", "Type"])
    for t in txns:
        writer.writerow([t.transaction_date, t.category, t.note or "", t.amount, t.transaction_type])

    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=khata_kitab_transactions.csv"}
    )

@app.route("/edit/<int:txn_id>", methods=["GET", "POST"])
@login_required
def edit_transaction(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    if txn.user_id != current_user.id:
        flash("You don't have permission to edit this transaction.")
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        txn.transaction_date = request.form.get("transaction_date")
        txn.transaction_type = request.form.get("transaction_type")
        txn.amount = float(request.form.get("amount"))
        txn.category = request.form.get("category")
        txn.note = request.form.get("note")
        db.session.commit()
        flash("Transaction updated successfully!")
        return redirect(url_for('dashboard'))

    return render_template("edit.html", txn=txn)

@app.route("/delete/<int:txn_id>")
@login_required
def delete_transaction(txn_id):
    txn = Transaction.query.get(txn_id)
    if txn and txn.user_id != current_user.id:
        flash("You don't have permission to delete this transaction.")
        return redirect(url_for('dashboard'))
    if txn:
        db.session.delete(txn)
        db.session.commit()
    flash("Transaction deleted successfully!")
    return redirect(url_for('dashboard'))

@app.route("/cancel-subscription/<int:sub_id>")
@login_required
def cancel_subscription(sub_id):
    sub = Subscription.query.get(sub_id)
    if sub and sub.user_id != current_user.id:
        flash("You don't have permission to cancel this subscription.")
        return redirect(url_for('dashboard'))
    if sub:
        db.session.delete(sub)
        db.session.commit()
    flash("Subscription cancelled successfully.")
    return redirect(url_for('dashboard'))

@app.route("/add-subscription", methods=["POST"])
@login_required
def add_subscription():
    sub = Subscription(
        user_id=current_user.id,
        name=request.form.get("name"),
        amount=float(request.form.get("amount")),
        billing_cycle=request.form.get("billing_cycle")
    )
    db.session.add(sub)
    db.session.commit()
    flash("Subscription added successfully!")
    return redirect(url_for('dashboard'))

@app.route("/set-budget", methods=["POST"])
@login_required
def set_budget():
    category = request.form.get("category")
    amount = float(request.form.get("amount"))
    budget = Budget.query.filter_by(user_id=current_user.id, category=category).first()
    if budget:
        budget.limit_amount = amount
    else:
        db.session.add(Budget(user_id=current_user.id, category=category, limit_amount=amount))
    db.session.commit()
    flash(f"Budget for {category} set to Rs. {amount:,.2f}")
    return redirect(url_for('dashboard'))

@app.route("/update-profile", methods=["POST"])
@login_required
def update_profile():
    new_name = request.form.get("name")
    current_user.name = new_name
    db.session.commit()
    flash("Personal operational configurations synchronized.")
    return redirect(url_for('profile'))

@app.route("/upload-profile-photo", methods=["POST"])
@login_required
def upload_profile_photo():
    file = request.files.get("photo")

    if not file or file.filename == "":
        flash("Please choose an image file to upload.")
        return redirect(url_for('profile'))

    if not allowed_file(file.filename):
        flash("Invalid file type. Please upload a PNG, JPG, GIF, or WEBP image.")
        return redirect(url_for('profile'))

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = secure_filename(f"user_{current_user.id}.{ext}")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    current_user.profile_pic = filename
    db.session.commit()
    flash("Profile photo updated successfully!")
    return redirect(url_for('profile'))

@app.route("/change-password", methods=["POST"])
@login_required
def change_password():
    current_pwd = request.form.get("current_password")
    new_pwd = request.form.get("new_password")
    confirm_pwd = request.form.get("confirm_password")

    if not check_password_hash(current_user.password_hash, current_pwd):
        flash("Current password is incorrect.")
        return redirect(url_for('profile'))

    if new_pwd != confirm_pwd:
        flash("Password sync validation mismatch! Please verify inputs.")
        return redirect(url_for('profile'))

    current_user.password_hash = generate_password_hash(new_pwd)
    db.session.commit()
    flash("Security parameters successfully updated.")
    return redirect(url_for('profile'))

# ---- Prevent cached pages from showing after logout (back-button fix) ----
@app.after_request
def add_no_cache_headers(response):
    if request.endpoint in ['dashboard', 'reports', 'profile', 'edit_transaction', 'feedback_page']:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    return response

if __name__ == "__main__":
    app.run(debug=True)