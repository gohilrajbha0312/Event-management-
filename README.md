# EventFlow — Event Management

EventFlow is a web application for discovering events, buying tickets, and managing listings. Organizers can publish events with details and banners; visitors browse, register, and pay via **UPI**; administrators oversee users and events. The app is built with **Flask** and **SQLite**, suitable for local development or deployment to platforms such as **Render**.

**Repository:** [Event-management-](https://github.com/gohilrajbha0312/Event-management-) on GitHub (this README uses the product name **EventFlow**).

---

## Project information

| Item | Description |
|------|-------------|
| **Purpose** | Browse events, purchase tickets with UPI-style checkout, and let organizers manage their events from a dashboard. |
| **Backend** | Python 3, Flask 3, SQLite (eventflow.db created on first run). |
| **Frontend** | Server-rendered HTML templates (Jinja2), CSS, minimal JavaScript. |
| **Payments** | UPI deep links and a merchant QR image; users confirm payment after paying in their UPI app. |
| **Roles** | **User** (browse and buy), **Organizer** (create and manage events), **Admin** (users, events, contact messages). |

### Main features

- Public event listing with search and filters (category, location, price).
- User accounts with login and session-based auth.
- Organizer dashboard: create and edit events, upload banners, view attendees.
- Admin dashboard: user management, event approval or suspension, contact form messages.
- Ticket checkout with order summary and UPI payment screen.
- Static pages: About, Contact, FAQ.

### Tech stack

- **Runtime:** Python 3
- **Framework:** Flask 3, Werkzeug, Flask-Login, Flask-WTF
- **Database:** SQLite 3
- **Production server:** Gunicorn (see 
ender.yaml)

---

## Requirements

- **Python** 3.11 or newer recommended (3.13 works for local development).
- **pip** for installing dependencies.

---

## Installation

### 1. Clone the repository

`ash
git clone https://github.com/gohilrajbha0312/Event-management-.git
cd Event-management-
`

If your folder name differs, change directory into the project root that contains pp.py.

### 2. Create a virtual environment (recommended)

**Windows (PowerShell)**

`powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
`

**macOS / Linux**

`ash
python3 -m venv .venv
source .venv/bin/activate
`

### 3. Install dependencies

`ash
pip install -r requirements.txt
`

### 4. Run the application

`ash
python app.py
`

Open **http://127.0.0.1:5000** in your browser.

On first start, the app creates eventflow.db, required tables, and (if the database is empty) demo users and sample events.

### 5. Stop the server

Press **Ctrl+C** in the terminal.

### Optional: run with Gunicorn (production-style)

After installing dependencies, you can test the same command used on Render:

`ash
gunicorn app:app --bind 127.0.0.1:5000
`

On Windows, Gunicorn is not officially supported; use python app.py for local development, or run under WSL/Linux.

---

## Configuration

- **UPI merchant** — In pp.py, set UPI_MERCHANT_ID and UPI_MERCHANT_NAME to your real UPI ID and display name so payment links and labels match your account.
- **Merchant QR image** — Replace static/images/upi-merchant-qr.png if you use a new QR screenshot; keep the filename or update the path in 	emplates/payment.html.
- **Secret key** — pp.secret_key is set in code for development. For production, use a strong random secret from an environment variable (do not commit real secrets).

---

## Demo accounts (fresh database only)

These are inserted only when the users table is empty:

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@eventflow.com | admin123 |
| Organizer | rajesh@eventflow.com | organizer123 |
| User | amit@eventflow.com | user123 |

Change these passwords in production and avoid using demo credentials on a public server.

---

## Production deployment (example: Render)

The repository includes 
ender.yaml with a sample **Render** configuration:

- **Build:** pip install -r requirements.txt
- **Start:** gunicorn app:app --bind 0.0.0.0:

Connect the GitHub repo in the Render dashboard and deploy as a **Web Service**, or use Blueprints from 
ender.yaml. SQLite on ephemeral disks resets when the instance restarts unless you attach persistent storage or use an external database.

---

## Project layout (overview)

`
├── app.py              # Flask app, routes, database init
├── requirements.txt    # Python dependencies
├── render.yaml         # Example Render.com service definition
├── eventflow.db        # SQLite DB (created at runtime)
├── static/             # CSS, uploads, UPI image
├── templates/          # HTML templates
└── README.md
`

---

## License

This project is provided as-is for development and learning. Add a license file if you intend to distribute or reuse the code under specific terms.
