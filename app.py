import os
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for, flash,
                   session, g, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'eventflow-secret-key-2026-super-secure'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# ─── UPI Merchant Configuration ─────────────────────────────────────
# Change this to your real UPI ID to receive payments
UPI_MERCHANT_ID = 'gohilrajbha1800@okicici'
UPI_MERCHANT_NAME = 'Raj Gohil'

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eventflow.db')

# ─── Database Helpers ───────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT DEFAULT 'General',
            location TEXT,
            venue TEXT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            end_date TEXT,
            end_time TEXT,
            price REAL DEFAULT 0,
            capacity INTEGER DEFAULT 100,
            banner TEXT,
            organizer_id INTEGER NOT NULL,
            status TEXT DEFAULT 'approved',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (organizer_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            total_price REAL DEFAULT 0,
            status TEXT DEFAULT 'confirmed',
            purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (event_id) REFERENCES events(id)
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            method TEXT DEFAULT 'card',
            status TEXT DEFAULT 'completed',
            transaction_id TEXT,
            paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticket_id) REFERENCES tickets(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    db.commit()
    db.close()

def seed_data():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    existing = db.execute("SELECT COUNT(*) as c FROM users").fetchone()['c']
    if existing > 0:
        db.close()
        return
    # Admin user
    db.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
               ("Admin", "admin@eventflow.com", generate_password_hash("admin123"), "admin"))
    # Demo organizer
    db.execute("INSERT INTO users (name, email, password, role, phone) VALUES (?, ?, ?, ?, ?)",
               ("Rajesh Patel", "rajesh@eventflow.com", generate_password_hash("organizer123"), "organizer", "+91-97250-10101"))
    # Demo user
    db.execute("INSERT INTO users (name, email, password, role, phone) VALUES (?, ?, ?, ?, ?)",
               ("Amit Shah", "amit@eventflow.com", generate_password_hash("user123"), "user", "+91-94260-20202"))

    # Sample events
    events = [
        ("Tech Summit Bhavnagar 2026", "Bhavnagar nu sabthee motu technology conference! Leading tech companies na keynote speakers, hands-on workshops, ane networking opportunities. AI, cloud computing, cybersecurity ane vadhare explore karo.",
         "Technology", "Bhavnagar, Gujarat", "Takhteshwar Hall", "2026-04-15", "09:00", "2026-04-17", "18:00", 499, 500, 2),
        ("Navratri Mahotsav 2026", "Bhavnagar na sabthee mota Navratri celebration ma jodao! 9 raato no garba-dandiya, live orchestra, ane food stalls sathe ek yaadgaar utsav. Traditional ane modern garba beats.",
         "Music", "Bhavnagar, Gujarat", "Khadia Ground", "2026-10-02", "19:00", "2026-10-10", "01:00", 299, 2000, 2),
        ("Startup Bhavnagar Pitch Night", "20 innovative Gujarat-based startups potaana ideas ek panel of investors ne present karshe. Founders, investors, ane tech enthusiasts sathe networking karo.",
         "Business", "Bhavnagar, Gujarat", "Hotel Sun N Shine, Waghawadi Road", "2026-03-28", "18:00", "2026-03-28", "22:00", 199, 200, 2),
        ("Kala Mela — Art & Craft Exhibition", "Gujarat ni lokakala ane modern art installations no anokho sangam. Award-winning artists ne malo, pottery ane block printing workshops attend karo.",
         "Art", "Bhavnagar, Gujarat", "Barton Museum", "2026-06-10", "10:00", "2026-06-12", "20:00", 99, 800, 2),
        ("Yoga & Wellness Camp", "Ek aakho divas mindfulness, yoga sessions, meditation workshops, ane healthy cooking demonstrations. Beginners ane experienced practitioners banne mate perfect.",
         "Health", "Bhavnagar, Gujarat", "Gaurishankar Lake Garden", "2026-04-05", "06:00", "2026-04-05", "17:00", 0, 150, 2),
        ("Kathiyawadi Food Festival", "Authentic Kathiyawadi ane Gujarati cuisine no anokho utsav! Live cooking demos, street food stalls, ane traditional recipes. Ek food lover nu swarg.",
         "Food", "Bhavnagar, Gujarat", "Victoria Park", "2026-07-08", "11:00", "2026-07-09", "21:00", 149, 600, 2),
    ]
    for ev in events:
        db.execute("""INSERT INTO events (title, description, category, location, venue, date, time, end_date, end_time, price, capacity, organizer_id)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", ev)

    # A few demo tickets
    db.execute("INSERT INTO tickets (user_id, event_id, quantity, total_price) VALUES (3, 1, 1, 499)")
    db.execute("INSERT INTO tickets (user_id, event_id, quantity, total_price) VALUES (3, 5, 2, 0)")
    db.execute("INSERT INTO payments (ticket_id, user_id, amount, method, transaction_id) VALUES (1, 3, 499, 'card', 'TXN-20260210-001')")

    db.commit()
    db.close()

# ─── Auth Decorator ─────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            if session.get('user_role') not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ─── Context Processor ──────────────────────────────────────────────

@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    return dict(current_user=user)

# ─── Home Page ──────────────────────────────────────────────────────

@app.route('/')
def home():
    db = get_db()
    upcoming_events = db.execute(
        "SELECT e.*, u.name as organizer_name FROM events e JOIN users u ON e.organizer_id = u.id WHERE e.status = 'approved' ORDER BY e.date ASC LIMIT 6"
    ).fetchall()
    stats = {
        'events': db.execute("SELECT COUNT(*) as c FROM events WHERE status='approved'").fetchone()['c'],
        'users': db.execute("SELECT COUNT(*) as c FROM users").fetchone()['c'],
        'tickets': db.execute("SELECT COUNT(*) as c FROM tickets").fetchone()['c'],
    }
    return render_template('home.html', events=upcoming_events, stats=stats)

# ─── Authentication ─────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_role'] = user['role']
            session['user_name'] = user['name']
            flash(f'Welcome back, {user["name"]}!', 'success')
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'organizer':
                return redirect(url_for('organizer_dashboard'))
            return redirect(url_for('user_dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        role = request.form.get('role', 'user')
        phone = request.form.get('phone', '').strip()

        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('signup.html')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('signup.html')
        if role not in ('user', 'organizer'):
            role = 'user'

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash('Email already registered.', 'danger')
            return render_template('signup.html')

        db.execute("INSERT INTO users (name, email, password, role, phone) VALUES (?, ?, ?, ?, ?)",
                   (name, email, generate_password_hash(password), role, phone))
        db.commit()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        session['user_id'] = user['id']
        session['user_role'] = user['role']
        session['user_name'] = user['name']
        flash('Account created successfully!', 'success')
        if role == 'organizer':
            return redirect(url_for('organizer_dashboard'))
        return redirect(url_for('user_dashboard'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user:
            flash('Password reset link has been sent to your email.', 'success')
        else:
            flash('No account found with that email.', 'danger')
    return render_template('forgot_password.html')

# ─── User Dashboard ─────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def user_dashboard():
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    tickets = db.execute("""
        SELECT t.*, e.title, e.date, e.time, e.location, e.venue, e.banner
        FROM tickets t JOIN events e ON t.event_id = e.id
        WHERE t.user_id = ? ORDER BY t.purchased_at DESC
    """, (session['user_id'],)).fetchall()
    return render_template('user_dashboard.html', user=user, tickets=tickets)

@app.route('/profile', methods=['POST'])
@login_required
def update_profile():
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    db = get_db()
    db.execute("UPDATE users SET name = ?, phone = ? WHERE id = ?",
               (name, phone, session['user_id']))
    db.commit()
    session['user_name'] = name
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('user_dashboard'))

# ─── Organizer Dashboard ────────────────────────────────────────────

@app.route('/organizer/dashboard')
@role_required('organizer', 'admin')
def organizer_dashboard():
    db = get_db()
    my_events = db.execute(
        "SELECT * FROM events WHERE organizer_id = ? ORDER BY created_at DESC",
        (session['user_id'],)
    ).fetchall()
    # Revenue
    total_revenue = 0
    event_stats = []
    for ev in my_events:
        tickets = db.execute(
            "SELECT COUNT(*) as count, COALESCE(SUM(total_price), 0) as revenue FROM tickets WHERE event_id = ?",
            (ev['id'],)
        ).fetchone()
        event_stats.append({
            'event': ev,
            'attendees': tickets['count'],
            'revenue': tickets['revenue']
        })
        total_revenue += tickets['revenue']
    return render_template('organizer_dashboard.html', event_stats=event_stats, total_revenue=total_revenue)

@app.route('/organizer/event/<int:event_id>/attendees')
@role_required('organizer', 'admin')
def event_attendees(event_id):
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id = ? AND organizer_id = ?",
                       (event_id, session['user_id'])).fetchone()
    if not event and session.get('user_role') != 'admin':
        flash('Event not found.', 'danger')
        return redirect(url_for('organizer_dashboard'))
    if not event:
        event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    attendees = db.execute("""
        SELECT u.name, u.email, t.quantity, t.total_price, t.purchased_at
        FROM tickets t JOIN users u ON t.user_id = u.id
        WHERE t.event_id = ?
    """, (event_id,)).fetchall()
    return render_template('attendees.html', event=event, attendees=attendees)

# ─── Admin Dashboard ────────────────────────────────────────────────

@app.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    db = get_db()
    users = db.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    events = db.execute("SELECT e.*, u.name as organizer_name FROM events e JOIN users u ON e.organizer_id = u.id ORDER BY e.created_at DESC").fetchall()
    total_revenue = db.execute("SELECT COALESCE(SUM(amount), 0) as total FROM payments").fetchone()['total']
    total_tickets = db.execute("SELECT COUNT(*) as c FROM tickets").fetchone()['c']
    stats = {
        'total_users': len(users),
        'total_events': len(events),
        'total_revenue': total_revenue,
        'total_tickets': total_tickets,
        'organizers': len([u for u in users if u['role'] == 'organizer']),
        'regular_users': len([u for u in users if u['role'] == 'user']),
    }
    contacts = db.execute("SELECT * FROM contacts ORDER BY created_at DESC LIMIT 10").fetchall()
    return render_template('admin_dashboard.html', users=users, events=events, stats=stats, contacts=contacts)

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@role_required('admin')
def delete_user(user_id):
    db = get_db()
    db.execute("DELETE FROM users WHERE id = ? AND role != 'admin'", (user_id,))
    db.commit()
    flash('User deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/event/<int:event_id>/toggle', methods=['POST'])
@role_required('admin')
def toggle_event(event_id):
    db = get_db()
    event = db.execute("SELECT status FROM events WHERE id = ?", (event_id,)).fetchone()
    new_status = 'suspended' if event['status'] == 'approved' else 'approved'
    db.execute("UPDATE events SET status = ? WHERE id = ?", (new_status, event_id))
    db.commit()
    flash(f'Event {"suspended" if new_status == "suspended" else "approved"}.', 'success')
    return redirect(url_for('admin_dashboard'))

# ─── Events ─────────────────────────────────────────────────────────

@app.route('/events')
def events():
    db = get_db()
    query = "SELECT e.*, u.name as organizer_name FROM events e JOIN users u ON e.organizer_id = u.id WHERE e.status = 'approved'"
    params = []

    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    location = request.args.get('location', '').strip()
    price_filter = request.args.get('price', '').strip()

    if search:
        query += " AND (e.title LIKE ? OR e.description LIKE ? OR e.location LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])
    if category:
        query += " AND e.category = ?"
        params.append(category)
    if location:
        query += " AND e.location LIKE ?"
        params.append(f'%{location}%')
    if price_filter == 'free':
        query += " AND e.price = 0"
    elif price_filter == 'paid':
        query += " AND e.price > 0"

    query += " ORDER BY e.date ASC"
    all_events = db.execute(query, params).fetchall()

    categories = db.execute("SELECT DISTINCT category FROM events WHERE status='approved'").fetchall()
    locations = db.execute("SELECT DISTINCT location FROM events WHERE status='approved'").fetchall()

    return render_template('events.html', events=all_events, categories=categories, locations=locations,
                           search=search, selected_category=category, selected_location=location, selected_price=price_filter)

@app.route('/event/<int:event_id>')
def event_detail(event_id):
    db = get_db()
    event = db.execute(
        "SELECT e.*, u.name as organizer_name, u.email as organizer_email FROM events e JOIN users u ON e.organizer_id = u.id WHERE e.id = ?",
        (event_id,)
    ).fetchone()
    if not event:
        flash('Event not found.', 'danger')
        return redirect(url_for('events'))

    tickets_sold = db.execute("SELECT COALESCE(SUM(quantity), 0) as sold FROM tickets WHERE event_id = ?", (event_id,)).fetchone()['sold']
    already_registered = False
    if 'user_id' in session:
        existing = db.execute("SELECT id FROM tickets WHERE user_id = ? AND event_id = ?",
                              (session['user_id'], event_id)).fetchone()
        already_registered = existing is not None

    return render_template('event_detail.html', event=event, tickets_sold=tickets_sold, already_registered=already_registered)

# ─── Create Event ───────────────────────────────────────────────────

@app.route('/create-event', methods=['GET', 'POST'])
@role_required('organizer', 'admin')
def create_event():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'General')
        location = request.form.get('location', '').strip()
        venue = request.form.get('venue', '').strip()
        date = request.form.get('date', '')
        time = request.form.get('time', '')
        end_date = request.form.get('end_date', '')
        end_time = request.form.get('end_time', '')
        price = float(request.form.get('price', 0) or 0)
        capacity = int(request.form.get('capacity', 100) or 100)

        banner_filename = None
        if 'banner' in request.files:
            file = request.files['banner']
            if file and file.filename:
                banner_filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], banner_filename))

        if not title or not date or not time:
            flash('Title, date, and time are required.', 'danger')
            return render_template('create_event.html')

        db = get_db()
        db.execute("""INSERT INTO events (title, description, category, location, venue, date, time, end_date, end_time, price, capacity, banner, organizer_id)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (title, description, category, location, venue, date, time, end_date, end_time, price, capacity, banner_filename, session['user_id']))
        db.commit()
        flash('Event created successfully!', 'success')
        return redirect(url_for('organizer_dashboard'))
    return render_template('create_event.html')

@app.route('/event/<int:event_id>/edit', methods=['GET', 'POST'])
@role_required('organizer', 'admin')
def edit_event(event_id):
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        flash('Event not found.', 'danger')
        return redirect(url_for('organizer_dashboard'))
    if event['organizer_id'] != session['user_id'] and session.get('user_role') != 'admin':
        flash('Unauthorized.', 'danger')
        return redirect(url_for('organizer_dashboard'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'General')
        location = request.form.get('location', '').strip()
        venue = request.form.get('venue', '').strip()
        date = request.form.get('date', '')
        time = request.form.get('time', '')
        end_date = request.form.get('end_date', '')
        end_time = request.form.get('end_time', '')
        price = float(request.form.get('price', 0) or 0)
        capacity = int(request.form.get('capacity', 100) or 100)

        banner_filename = event['banner']
        if 'banner' in request.files:
            file = request.files['banner']
            if file and file.filename:
                banner_filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], banner_filename))

        db.execute("""UPDATE events SET title=?, description=?, category=?, location=?, venue=?, date=?, time=?, end_date=?, end_time=?, price=?, capacity=?, banner=?
                      WHERE id=?""",
                   (title, description, category, location, venue, date, time, end_date, end_time, price, capacity, banner_filename, event_id))
        db.commit()
        flash('Event updated successfully!', 'success')
        return redirect(url_for('organizer_dashboard'))
    return render_template('create_event.html', event=event, edit=True)

@app.route('/event/<int:event_id>/delete', methods=['POST'])
@role_required('organizer', 'admin')
def delete_event(event_id):
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if event and (event['organizer_id'] == session['user_id'] or session.get('user_role') == 'admin'):
        db.execute("DELETE FROM tickets WHERE event_id = ?", (event_id,))
        db.execute("DELETE FROM events WHERE id = ?", (event_id,))
        db.commit()
        flash('Event deleted.', 'success')
    return redirect(url_for('organizer_dashboard'))

# ─── Payment / Registration ─────────────────────────────────────────

@app.route('/event/<int:event_id>/register', methods=['GET', 'POST'])
@login_required
def register_event(event_id):
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id = ? AND status = 'approved'", (event_id,)).fetchone()
    if not event:
        flash('Event not found.', 'danger')
        return redirect(url_for('events'))

    existing = db.execute("SELECT id FROM tickets WHERE user_id = ? AND event_id = ?",
                          (session['user_id'], event_id)).fetchone()
    if existing:
        flash('You are already registered for this event.', 'info')
        return redirect(url_for('event_detail', event_id=event_id))

    quantity = int(request.args.get('qty', 1))
    total = event['price'] * quantity

    if event['price'] == 0:
        # Free event — register directly
        db.execute("INSERT INTO tickets (user_id, event_id, quantity, total_price) VALUES (?, ?, ?, 0)",
                   (session['user_id'], event_id, quantity))
        db.commit()
        flash('Successfully registered for the event!', 'success')
        return redirect(url_for('payment_success', event_id=event_id))

    # Generate UPI deep link
    from urllib.parse import quote
    upi_note = f"EventFlow - {event['title']}"
    upi_link = f"upi://pay?pa={UPI_MERCHANT_ID}&pn={quote(UPI_MERCHANT_NAME)}&am={total:.2f}&cu=INR&tn={quote(upi_note)}"

    return render_template('payment.html', event=event, quantity=quantity, total=total,
                           upi_link=upi_link, upi_merchant_id=UPI_MERCHANT_ID, upi_merchant_name=UPI_MERCHANT_NAME)

@app.route('/event/<int:event_id>/pay', methods=['POST'])
@login_required
def process_payment(event_id):
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        flash('Event not found.', 'danger')
        return redirect(url_for('events'))

    quantity = int(request.form.get('quantity', 1))
    total = event['price'] * quantity

    # Create ticket
    db.execute("INSERT INTO tickets (user_id, event_id, quantity, total_price) VALUES (?, ?, ?, ?)",
               (session['user_id'], event_id, quantity, total))
    db.commit()
    ticket = db.execute("SELECT last_insert_rowid() as id").fetchone()

    # Create payment record
    txn_id = f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{ticket['id']}"
    db.execute("INSERT INTO payments (ticket_id, user_id, amount, method, transaction_id) VALUES (?, ?, ?, ?, ?)",
               (ticket['id'], session['user_id'], total, request.form.get('method', 'upi'), txn_id))
    db.commit()

    flash('Payment successful! You are registered.', 'success')
    return redirect(url_for('payment_success', event_id=event_id))

@app.route('/event/<int:event_id>/success')
@login_required
def payment_success(event_id):
    db = get_db()
    event = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    ticket = db.execute("SELECT * FROM tickets WHERE user_id = ? AND event_id = ? ORDER BY id DESC LIMIT 1",
                        (session['user_id'], event_id)).fetchone()
    payment = None
    if ticket:
        payment = db.execute("SELECT * FROM payments WHERE ticket_id = ?", (ticket['id'],)).fetchone()
    return render_template('payment_success.html', event=event, ticket=ticket, payment=payment)

# ─── Static Pages ───────────────────────────────────────────────────

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        if name and email and message:
            db = get_db()
            db.execute("INSERT INTO contacts (name, email, subject, message) VALUES (?, ?, ?, ?)",
                       (name, email, subject, message))
            db.commit()
            flash('Your message has been sent successfully!', 'success')
            return redirect(url_for('contact'))
        flash('Please fill in all required fields.', 'danger')
    return render_template('contact.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

# ─── Initialize and Run ─────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    seed_data()
    app.run(debug=True, port=5000)
