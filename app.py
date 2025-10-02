# Sydney Chess Club Admin Portal - Flask Application

# This file contains all backend logic for the Sydney Chess Club Admin Portal web app.

# Features implemented in this file:
#   - Secure admin-only authentication (login, signup, logout, password change)
#   - Admin management (add, edit, delete, change password for admins)
#   - Member management (add, edit, delete, view members)
#   - Tournament management (create, edit, delete tournaments)
#   - Participant selection for tournaments
#   - Fixture generation for Swiss, Knockout, and Round Robin formats (with correct bye handling)
#   - View and clear round 1 fixtures for tournaments
#   - Export round 1 fixtures to CSV
#   - Dashboard with dynamic stats (total members, completed tournaments, admins, upcoming tournaments)
#   - Completed tournaments listing
#   - Reports and analytics (total members, average rating, recent member, total tournaments)
#   - Modal-based UI for admin/member/tournament actions (error handling, flash messages)
#   - All routes protected by login where appropriate
#   - Utility API endpoint for total members
#   - All code is extensively commented for maintainability and onboarding


from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
import sqlite3
import bcrypt
import os
import re
from datetime import datetime, date, timedelta
from functools import wraps
import random
import secrets

# --- Database Connection Helper ---
def get_db_connection():
    # Create a new database connection using a context manager.
    # Sets row_factory to sqlite3.Row for dict-like access to columns.
    conn = sqlite3.connect('data/main.db')
    conn.row_factory = sqlite3.Row
    # Enforce foreign key constraints
    try:
        conn.execute('PRAGMA foreign_keys = ON')
    except Exception:
        pass
    return conn

# --- Authentication Decorator ---
def login_required(f):
    # Decorator to require login for protected routes.
    # Redirects to login page if user is not authenticated.
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('You must be logged in to access this page', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Jinja Date Formatting Filter ---
def datetimeformat(value, format='%d-%m-%Y'):
    """
    Format date strings for display in templates.
    Tries ISO and fallback to YYYY-MM-DD.
    """
    try:
        dt = datetime.fromisoformat(value)
    except Exception:
        try:
            dt = datetime.strptime(value, '%Y-%m-%d')
        except Exception:
            return value  # fallback: return as is
    return dt.strftime(format)

# --- Flask App Setup ---
app = Flask(__name__)

# App configuration and security defaults
APP_ENV = os.environ.get('APP_ENV', 'development')
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')
if APP_ENV == 'production' and not SECRET_KEY:
    raise RuntimeError('FLASK_SECRET_KEY must be set in production')
app.secret_key = SECRET_KEY or 'dev_secret_key'

# Secure cookie settings
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Strict',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)

# Simple CSRF protection
@app.before_request
def ensure_csrf_and_session():
    # Create a CSRF token for the session if missing
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    # Enforce CSRF on all POST requests
    if request.method == 'POST':
        token = request.form.get('csrf_token')
        if not token or token != session.get('csrf_token'):
            abort(400)

# Security headers
@app.after_request
def set_security_headers(resp):
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['Referrer-Policy'] = 'no-referrer'
    # CSP: allow self + required CDNs for fonts/icons/charts
    csp = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    resp.headers['Content-Security-Policy'] = csp
    # HSTS (only makes sense over HTTPS)
    if request.scheme == 'https':
        resp.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    return resp

# Template helpers
@app.context_processor
def inject_globals():
    allow_signup = False
    # Allow signup only if ADMIN_SIGNUP_SECRET is set (invite code required)
    if os.environ.get('ADMIN_SIGNUP_SECRET'):
        allow_signup = True
    return dict(csrf_token=session.get('csrf_token'), allow_signup=allow_signup, APP_ENV=APP_ENV)
app.jinja_env.filters['datetimeformat'] = datetimeformat

# --- FLASK ROUTES ---

@app.route('/')
def index():
    # Homepage: show upcoming tournaments, completed tournaments count, admins, and total members.
    # Gathers summary stats for dashboard display.
    today = datetime.now().date().isoformat()
    with get_db_connection() as conn:
        tournaments = conn.execute('SELECT * FROM tournaments WHERE date >= ? ORDER BY date', (today,)).fetchall()
        completed_tournaments_count = conn.execute('SELECT COUNT(*) FROM tournaments WHERE date < ?', (today,)).fetchone()[0]
        admins = conn.execute('SELECT * FROM users').fetchall()
        total_members = conn.execute('SELECT COUNT(*) FROM members').fetchone()[0]
    return render_template(
        'index.html',
        tournaments=tournaments,
        completed_tournaments_count=completed_tournaments_count,
        members=admins,
        total_members=total_members
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Admin login route. Only users in the users table can log in.
    # - GET: Show login form
    # - POST: Validate credentials, set session, redirect to dashboard
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Fetch user from DB
        with get_db_connection() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user is not None:
            user_password_hash = user['password_hash'] if 'password_hash' in user.keys() else user[1]
            # Check password using bcrypt
            if user_password_hash and bcrypt.checkpw(password.encode('utf-8'), user_password_hash):
                # Rotate session to prevent fixation
                session.clear()
                session['username'] = username
                session['csrf_token'] = secrets.token_hex(32)
                flash('Logged in successfully', 'success')
                return redirect(url_for('index'))
        # Generic error to prevent user enumeration
        error = "Invalid username or password."
    return render_template('login.html', error=error)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # Admin signup route. Guarded by invite code via ADMIN_SIGNUP_SECRET.
    # - GET: Show signup form
    # - POST: Validate and create new admin user, log in
    # Enforce invite-based signup
    if not os.environ.get('ADMIN_SIGNUP_SECRET'):
        flash('Admin signup is disabled. Contact an existing administrator.', 'danger')
        return redirect(url_for('login'))
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        invite_code = request.form.get('invite_code', '')
        if invite_code != os.environ.get('ADMIN_SIGNUP_SECRET'):
            error = "Invalid invite code."
        # Username and password validation
        elif any(c.isspace() for c in username):
            error = "Username cannot contain spaces or whitespace."
        elif len(password) < 8:
            error = "Password must be at least 8 characters long."
        elif not re.search(r'[A-Za-z]', password):
            error = "Password must contain at least one letter."
        elif not re.search(r'\d', password):
            error = "Password must contain at least one number."
        elif not re.search(r'[^A-Za-z0-9]', password):
            error = "Password must contain at least one special character."
        else:
            with get_db_connection() as conn:
                existing_user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
                if existing_user:
                    error = "Username already exists."
                else:
                    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                    conn.execute(
                        'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                        (username, hashed_pw)
                    )
                    conn.commit()
                    session.clear()
                    session['username'] = username
                    session['csrf_token'] = secrets.token_hex(32)
                    flash('Account created and logged in!', 'success')
                    return redirect(url_for('index'))
    return render_template('signup.html', error=error)

@app.route('/logout')
def logout():
    # Log out the current user and clear session.
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

def _suggested_tournament_date():
    """Return the next weekend date (Saturday/Sunday) as YYYY-MM-DD."""
    today = date.today()
    for offset in range(1, 8):
        candidate = today + timedelta(days=offset)
        if candidate.weekday() in (5, 6):
            return candidate.strftime('%Y-%m-%d')
    return (today + timedelta(days=7)).strftime('%Y-%m-%d')


def _get_saved_locations(limit=6):
    with get_db_connection() as conn:
        rows = conn.execute(
            'SELECT location, COUNT(*) as usage_count FROM tournaments GROUP BY location HAVING location != "" ORDER BY usage_count DESC, location ASC LIMIT ?'
        , (limit,)).fetchall()
    return [row['location'] for row in rows if row['location']]


@app.route('/create-tournament', methods=['GET', 'POST'])
@login_required
def create_tournament():
    # Create a new tournament (admin only).
    # - GET: Show tournament creation form with smart defaults and saved venues
    # - POST: Validate and insert tournament, redirect to management screen
    suggested_date = _suggested_tournament_date()
    saved_locations = _get_saved_locations()
    default_location_choice = saved_locations[0] if saved_locations else 'custom'
    form_values = {
        'name': '',
        'date': suggested_date,
        'location': default_location_choice if default_location_choice != 'custom' else '',
        'location_choice': default_location_choice,
        'custom_location': '',
        'format': ''
    }

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        date_value = request.form.get('date', '').strip()
        format_ = request.form.get('format', '').strip()
        location_choice = request.form.get('location_choice', '').strip()
        custom_location = request.form.get('custom_location', '').strip()
        location = custom_location if location_choice == 'custom' else location_choice

        form_values.update({
            'name': name,
            'date': date_value or suggested_date,
            'location': location,
            'location_choice': location_choice if location_choice else '',
            'custom_location': custom_location,
            'format': format_
        })

        # Basic validation for all fields
        if location_choice == 'custom' and not custom_location:
            flash('Please enter the custom venue name.', 'danger')
            return render_template('create-tournament.html', saved_locations=saved_locations, suggested_date=suggested_date, form_values=form_values)

        if not name or not date_value or not location or not format_:
            flash('Please complete all required fields before continuing.', 'danger')
            return render_template('create-tournament.html', saved_locations=saved_locations, suggested_date=suggested_date, form_values=form_values)
        try:
            datetime.strptime(date_value, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
            return render_template('create-tournament.html', saved_locations=saved_locations, suggested_date=suggested_date, form_values=form_values)
        # Insert tournament and get new ID
        with get_db_connection() as conn:
            cur = conn.execute(
                'INSERT INTO tournaments (name, date, location, format) VALUES (?, ?, ?, ?)',
                (name, date_value, location, format_)
            )
            tournament_id = cur.lastrowid
            conn.commit()
        flash('Tournament created successfully! Manage details, participants, and fixtures below.', 'success')
        return redirect(url_for('edit_tournament', tournament_id=tournament_id))

    return render_template('create-tournament.html', saved_locations=saved_locations, suggested_date=suggested_date, form_values=form_values)

@app.route('/edit-tournament/<int:tournament_id>', methods=['GET', 'POST'])
@login_required
def edit_tournament(tournament_id):
    """Unified management screen for tournament details, participants, and fixtures."""
    intent = request.form.get('intent')
    with get_db_connection() as conn:
        tournament = conn.execute('SELECT * FROM tournaments WHERE id = ?', (tournament_id,)).fetchone()
        if not tournament:
            flash('Tournament not found', 'danger')
            return redirect(url_for('index'))

        if request.method == 'POST':
            if intent == 'update_details':
                name = request.form['name'].strip()
                date_value = request.form['date']
                location = request.form['location'].strip()
                format_ = request.form['format']

                if not name or not date_value or not location or not format_:
                    flash('All tournament fields are required.', 'danger')
                    return redirect(url_for('edit_tournament', tournament_id=tournament_id))
                try:
                    datetime.strptime(date_value, '%Y-%m-%d')
                except ValueError:
                    flash('Invalid date format. Use YYYY-MM-DD.', 'danger')
                    return redirect(url_for('edit_tournament', tournament_id=tournament_id))

                conn.execute(
                    'UPDATE tournaments SET name = ?, date = ?, location = ?, format = ? WHERE id = ?',
                    (name, date_value, location, format_, tournament_id)
                )
                conn.commit()
                flash('Tournament details updated successfully.', 'success')
                return redirect(url_for('edit_tournament', tournament_id=tournament_id))

            if intent == 'save_participants':
                selected = request.form.getlist('participants')
                conn.execute('DELETE FROM tournament_participants WHERE tournament_id = ?', (tournament_id,))
                for member_id in selected:
                    conn.execute(
                        'INSERT INTO tournament_participants (tournament_id, member_id) VALUES (?, ?)',
                        (tournament_id, int(member_id))
                    )
                conn.commit()
                flash('Participants updated.', 'success')
                return redirect(url_for('edit_tournament', tournament_id=tournament_id, _anchor='participants'))

        members = conn.execute('SELECT * FROM members ORDER BY rating DESC, name ASC').fetchall()
        selected_ids = {
            row['member_id']
            for row in conn.execute(
                'SELECT member_id FROM tournament_participants WHERE tournament_id = ?',
                (tournament_id,)
            ).fetchall()
        }
        fixtures = conn.execute('''
            SELECT f.*, m1.name as player1_name, m2.name as player2_name
            FROM fixtures f
            JOIN members m1 ON f.player1_id = m1.id
            LEFT JOIN members m2 ON f.player2_id = m2.id
            WHERE f.tournament_id = ? AND f.round = 1
            ORDER BY f.id
        ''', (tournament_id,)).fetchall()

    return render_template(
        'edit-tournament.html',
        tournament=tournament,
        members=members,
        selected_ids=selected_ids,
        fixtures=fixtures
    )

@app.route('/delete_tournament/<int:tournament_id>', methods=['POST'])
@login_required
def delete_tournament(tournament_id):
    # Delete a tournament.
    with get_db_connection() as conn:
        conn.execute('DELETE FROM tournaments WHERE id = ?', (tournament_id,))
        conn.commit()
    flash('Tournament deleted successfully', 'success')
    return redirect(url_for('index'))

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    # Delete the current admin's account and log out (POST only, CSRF protected).
    username = session['username']
    with get_db_connection() as conn:
        conn.execute('DELETE FROM users WHERE username = ?', (username,))
        conn.commit()
    session.clear()
    flash('Your account has been deleted', 'success')
    return redirect(url_for('index'))

@app.route('/manage-members')
@login_required
def manage_members():
    # View and manage all club members (admin only).
    # Shows a table of all members, sorted by rating and name.
    with get_db_connection() as conn:
        members = conn.execute('SELECT * FROM members ORDER BY rating DESC, name ASC').fetchall()
    return render_template('members.html', members=members)

@app.route('/add_member', methods=['POST'])
@login_required
def add_member():
    # Add a new club member.
    # Accepts name, email, and rating from form.
    name = request.form['name']
    email = request.form.get('email')
    rating = request.form.get('rating', 1200)
    with get_db_connection() as conn:
        conn.execute(
            'INSERT INTO members (name, email, rating) VALUES (?, ?, ?)',
            (name, email, rating)
        )
        conn.commit()
        flash('Member added successfully', 'success')
    return redirect(url_for('manage_members'))

@app.route('/delete_member/<int:member_id>', methods=['POST'])
@login_required
def delete_member(member_id):
    # Delete a club member.
    with get_db_connection() as conn:
        conn.execute('DELETE FROM members WHERE id = ?', (member_id,))
        conn.commit()
    flash('Member deleted', 'success')
    return redirect(url_for('manage_members'))

@app.route('/reports')
@login_required
def reports():
    with get_db_connection() as conn:
        # Stat tiles
        total_members = conn.execute('SELECT COUNT(*) FROM members').fetchone()[0]
        avg_rating = conn.execute('SELECT AVG(rating) FROM members').fetchone()[0]
        total_tournaments = conn.execute('SELECT COUNT(*) FROM tournaments').fetchone()[0]
        recent = conn.execute('SELECT name FROM members ORDER BY joined_at DESC LIMIT 1').fetchone()
        recent_member = recent['name'] if recent else '—'

        # Membership growth (last 12 months)
        growth_data = {'labels': [], 'values': []}
        rows = conn.execute("""
            SELECT strftime('%Y-%m', joined_at) as ym, COUNT(*) as count
            FROM members
            WHERE joined_at IS NOT NULL
            GROUP BY ym
            ORDER BY ym DESC
            LIMIT 12
        """).fetchall()
        for row in reversed(rows):
            growth_data['labels'].append(row['ym'] or '')
            growth_data['values'].append(row['count'] or 0)
        # Pad with zeros if less than 12 months
        while len(growth_data['labels']) < 12:
            growth_data['labels'].insert(0, '')
            growth_data['values'].insert(0, 0)

        # Tournament format distribution
        format_data = {'labels': [], 'values': []}
        formats = conn.execute("SELECT format, COUNT(*) as count FROM tournaments GROUP BY format").fetchall()
        for row in formats:
            format_data['labels'].append(row['format'] or 'Unknown')
            format_data['values'].append(row['count'] or 0)

        # Top 5 members by rating
        top_members = conn.execute("SELECT name, rating FROM members ORDER BY rating DESC LIMIT 5").fetchall()

        # Recent admin activity (dummy example, replace with real log if available)
        admin_activity = [
            {'username': 'ezradevs', 'action': 'Added member', 'date': '2025-07-01'},
            {'username': 'mr.saurine', 'action': 'Created tournament', 'date': '2025-06-28'},
            {'username': 'ezradevs', 'action': 'Created tournament', 'date': '2025-06-28'},
            {'username': 'admin', 'action': 'Edited member', 'date': '2025-06-25'},
            {'username': 'test', 'action': 'Deleted member', 'date': '2025-06-20'},
            {'username': 'ezradevs', 'action': 'Deleted tournament', 'date': '2025-06-15'},
        ]

    return render_template(
        'reports.html',
        total_members=total_members,
        avg_rating=int(avg_rating) if avg_rating else '—',
        total_tournaments=total_tournaments,
        recent_member=recent_member,
        growth_data=growth_data,
        format_data=format_data,
        top_members=top_members,
        admin_activity=admin_activity
    )

@app.route('/edit_member/<int:member_id>', methods=['POST'])
@login_required
def edit_member(member_id):
    # Edit a club member's details.
    # Accepts name, email, and rating from form and updates the member.
    name = request.form['name']
    email = request.form.get('email')
    rating = request.form.get('rating', 1200)
    with get_db_connection() as conn:
        conn.execute(
            'UPDATE members SET name = ?, email = ?, rating = ? WHERE id = ?',
            (name, email, rating, member_id)
        )
        conn.commit()
        flash('Member updated successfully', 'success')
    return redirect(url_for('manage_members'))

@app.route('/tournament/<int:tournament_id>/generate_fixtures', methods=['POST'])
@login_required
def generate_fixtures(tournament_id):
    # Generate round 1 fixtures for a tournament (Swiss, Knockout, or Round Robin).
    # - Deletes any existing round 1 fixtures for the tournament
    # - Pairs participants according to the selected format
    # - Handles byes for odd numbers
    # - Saves fixtures to the database
    with get_db_connection() as conn:
        tournament = conn.execute('SELECT * FROM tournaments WHERE id = ?', (tournament_id,)).fetchone()
        format_ = tournament['format']
        participants = [row['member_id'] for row in conn.execute('SELECT member_id FROM tournament_participants WHERE tournament_id = ?', (tournament_id,)).fetchall()]
        conn.execute('DELETE FROM fixtures WHERE tournament_id = ? AND round = 1', (tournament_id,))
        if not participants or len(participants) < 2:
            flash('At least 2 participants required to generate fixtures', 'danger')
            return redirect(url_for('edit_tournament', tournament_id=tournament_id, _anchor='participants'))
        members = {row['id']: row for row in conn.execute('SELECT * FROM members WHERE id IN ({seq})'.format(seq=','.join(['?']*len(participants))), participants)}
        pairings = []
        n = len(participants)
        # Pairing logic for each tournament format
        if format_ == 'Swiss':
            # Swiss: top half vs bottom half by rating
            sorted_participants = sorted(participants, key=lambda x: -members[x]['rating'])
            mid = n // 2
            top = sorted_participants[:mid]
            bottom = sorted_participants[mid:]
            for i in range(min(len(top), len(bottom))):
                pairings.append((top[i], bottom[i]))
            if len(top) < len(bottom):
                pairings.append((bottom[-1], None))
        elif format_ == 'Knockout':
            # Knockout: random shuffle, pair off, last gets bye if odd
            shuffled = participants[:]
            random.shuffle(shuffled)
            for i in range(0, n-1, 2):
                pairings.append((shuffled[i], shuffled[i+1]))
            if n % 2 == 1:
                pairings.append((shuffled[-1], None))
        elif format_ == 'Round-robin':
            # Round-robin: pair first vs last, second vs second-last, etc.
            players = participants[:]
            if n % 2 == 1:
                players.append(None)
                n += 1
            half = n // 2
            used = set()
            for i in range(half):
                p1 = players[i]
                p2 = players[n - 1 - i]
                if p1 is not None and p2 is not None:
                    pairings.append((p1, p2))
                    used.add(p1)
                    used.add(p2)
                elif p1 is not None and p2 is None:
                    pairings.append((p1, None))
                    used.add(p1)
                elif p2 is not None and p1 is None:
                    pairings.append((p2, None))
                    used.add(p2)
            for pid in participants:
                if pid not in used:
                    pairings.append((pid, None))
        # Save fixtures, including byes
        for p1, p2 in pairings:
            result = '1-0' if p2 is None else 'TBD'
            conn.execute('INSERT INTO fixtures (tournament_id, round, player1_id, player2_id, result) VALUES (?, 1, ?, ?, ?)', (tournament_id, p1, p2, result))
        conn.commit()
        flash('Fixtures generated for Round 1', 'success')
    return redirect(url_for('edit_tournament', tournament_id=tournament_id, _anchor='fixtures'))

@app.route('/api/total_members')
@login_required
def api_total_members():
    # API endpoint: return total number of club members (admin only).
    # Returns JSON with total member count.
    with get_db_connection() as conn:
        total_members = conn.execute('SELECT COUNT(*) FROM members').fetchone()[0]
    return jsonify({'total_members': total_members})

@app.route('/completed-tournaments')
@login_required
def completed_tournaments():
    # Show all completed tournaments (admin only).
    # Lists tournaments with a date before today.
    today = date.today().isoformat()
    with get_db_connection() as conn:
        tournaments = conn.execute('SELECT * FROM tournaments WHERE date < ? ORDER BY date DESC', (today,)).fetchall()
    return render_template('completed-tournaments.html', tournaments=tournaments)

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    # Change password for self or another admin (modal-based, admin only).
    # - If admin_id is present, change another admin's password
    # - Otherwise, change own password (requires current password)
    # - Validates password strength and confirmation
    # - On error, redirects with modal open and error message
    error = None
    admin_id = request.form.get('admin_id')
    # Treat as admin password change if admin_id is present and not empty
    is_admin_pw_change = admin_id is not None and str(admin_id).strip() != ''
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        # Password validation
        if new_password != confirm_password:
            error = 'New passwords do not match.'
        elif len(new_password) < 8 or not any(c.isalpha() for c in new_password) or not any(c.isdigit() for c in new_password) or not any(not c.isalnum() for c in new_password):
            error = 'Password must be at least 8 characters and include a letter, a number, and a special character'
        else:
            if is_admin_pw_change:  # Changing another admin's password
                with get_db_connection() as conn:
                    admin = conn.execute('SELECT * FROM users WHERE id = ?', (admin_id,)).fetchone()
                    if not admin:
                        error = 'Administrator not found.'
                    else:
                        hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                        conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (hashed_pw, admin_id))
                        conn.commit()
                        flash('Administrator password changed successfully', 'success')
                        return redirect(url_for('manage_admins'))
            else:  # Changing own password
                username = session['username']
                with get_db_connection() as conn:
                    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
                    if not user or not current_password or not bcrypt.checkpw(current_password.encode('utf-8'), user['password_hash']):
                        error = 'Current password is incorrect'
                    else:
                        hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                        conn.execute('UPDATE users SET password_hash = ? WHERE username = ?', (hashed_pw, username))
                        conn.commit()
                        flash('Password changed successfully', 'success')
                        return redirect(url_for('index'))
    # On error, redirect with modal open and error message
    if error:
        if is_admin_pw_change:
            return redirect(url_for('manage_admins', show_change_admin_password_modal=admin_id, change_admin_password_error=error))
        else:
            return redirect(url_for('index', show_change_password_modal=1, change_password_error=error))
    if is_admin_pw_change:
        return redirect(url_for('manage_admins'))
    return redirect(url_for('index'))

@app.route('/tournament/<int:tournament_id>/export_fixtures_csv')
@login_required
def export_fixtures_csv(tournament_id):
    # Export round 1 fixtures for a tournament as a CSV file.
    # - Fetches all round 1 fixtures for the tournament
    # - Returns a CSV file as a Flask Response
    import csv
    from io import StringIO
    with get_db_connection() as conn:
        fixtures = conn.execute('''
            SELECT f.id, m1.name as player1_name, m2.name as player2_name, f.result
            FROM fixtures f
            JOIN members m1 ON f.player1_id = m1.id
            LEFT JOIN members m2 ON f.player2_id = m2.id
            WHERE f.tournament_id = ? AND f.round = 1
            ORDER BY f.id
        ''', (tournament_id,)).fetchall()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Fixture ID', 'Player 1', 'Player 2', 'Result'])
    for fixture in fixtures:
        writer.writerow([
            fixture['id'],
            fixture['player1_name'],
            fixture['player2_name'] if fixture['player2_name'] else 'BYE',
            fixture['result']
        ])
    output = si.getvalue()
    from flask import Response
    return Response(
        output,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=round1_fixtures_tournament_{tournament_id}.csv'
        }
    )

@app.route('/manage-admins')
@login_required
def manage_admins():
    # View and manage all administrators.
    # Shows a table of all admin users.
    with get_db_connection() as conn:
        admins = conn.execute('SELECT * FROM users ORDER BY username ASC').fetchall()
    return render_template('manage-admins.html', admins=admins)

@app.route('/edit_admin/<int:admin_id>', methods=['GET', 'POST'])
@login_required
def edit_admin(admin_id):
    # Edit an administrator's username (admin only, modal-based).
    # - GET: Show edit form
    # - POST: Update username
    with get_db_connection() as conn:
        admin = conn.execute('SELECT * FROM users WHERE id = ?', (admin_id,)).fetchone()
        if not admin:
            flash('Administrator not found', 'danger')
            return redirect(url_for('manage_admins'))
        if request.method == 'POST':
            username = request.form['username'].strip()
            if not username:
                flash('Username cannot be empty', 'danger')
                return redirect(url_for('edit_admin', admin_id=admin_id))
            conn.execute('UPDATE users SET username = ? WHERE id = ?', (username, admin_id))
            conn.commit()
            flash('Administrator updated successfully', 'success')
            return redirect(url_for('manage_admins'))
    # Render via modal in manage-admins; fallback template not used
    return render_template('manage-admins.html', admins=[admin])

@app.route('/delete_admin/<int:admin_id>', methods=['POST'])
@login_required
def delete_admin(admin_id):
    # Delete an administrator. Secure code required for deleting other admins. Self-deletion logs out.
    # - If deleting self, log out after delete
    # - If deleting another admin, require secure code
    if session.get('username'):
        with get_db_connection() as conn:
            admin = conn.execute('SELECT * FROM users WHERE id = ?', (admin_id,)).fetchone()
            if not admin:
                flash('Administrator not found', 'danger')
            elif admin['username'] == session['username']:
                # Self-deletion: log out after delete
                conn.execute('DELETE FROM users WHERE id = ?', (admin_id,))
                conn.commit()
                session.clear()
                flash('Your administrator account has been deleted. You have been logged out', 'success')
                return redirect(url_for('login'))
            else:
                # Require secure code for deleting other admins
                secure_code = request.form.get('secure_code', '')
                expected_code = os.environ.get('ADMIN_DELETE_CODE')
                if not expected_code or secure_code != expected_code:
                    flash('Incorrect secure code. Administrator not deleted', 'danger')
                    return redirect(url_for('manage_admins'))
                conn.execute('DELETE FROM users WHERE id = ?', (admin_id,))
                conn.commit()
                flash('Administrator deleted', 'success')
    return redirect(url_for('manage_admins'))

@app.route('/add_admin', methods=['POST'])
@login_required
def add_admin():
    # Add a new administrator (modal-based, admin only). Validates username and password.
    # - Validates all fields and password strength
    # - On error, redirects with modal open and error message
    username = request.form['username'].strip()
    password = request.form['password']
    password_confirm = request.form['password_confirm']
    error = None
    # Validation for all fields and password strength
    if not username or not password or not password_confirm:
        error = 'All fields are required.'
    elif password != password_confirm:
        error = 'Passwords do not match.'
    elif any(c.isspace() for c in username):
        error = 'Username cannot contain spaces or whitespace.'
    elif len(password) < 8 or not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password) or not re.search(r'[^A-Za-z0-9]', password):
        error = 'Password must be at least 8 characters, contain a letter, a number, and a special character.'
    else:
        with get_db_connection() as conn:
            existing_user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            if existing_user:
                error = 'Username already exists.'
            else:
                hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, hashed_pw))
                conn.commit()
                flash('Administrator added successfully', 'success')
                return redirect(url_for('manage_admins'))
    # On error, redirect with modal open and error message
    if error:
        return redirect(url_for('manage_admins', show_add_admin_modal=1, add_admin_error=error))
    return redirect(url_for('manage_admins'))

@app.route('/tournament/<int:tournament_id>/clear_fixtures', methods=['POST'])
@login_required
def clear_fixtures(tournament_id):
    # Clear all fixtures for the given tournament.
    # Deletes all fixture records for the specified tournament.
    with get_db_connection() as conn:
        conn.execute('DELETE FROM fixtures WHERE tournament_id = ?', (tournament_id,))
        conn.commit()
    flash('All fixtures cleared for this tournament', 'success')
    return redirect(url_for('edit_tournament', tournament_id=tournament_id, _anchor='fixtures'))

if __name__ == '__main__':
    # Run the Flask app. Use FLASK_DEBUG=1 to enable debug.
    debug_mode = os.environ.get('FLASK_DEBUG') == '1'
    app.run(host='0.0.0.0', port=3000, debug=debug_mode)
