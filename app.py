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
from collections import defaultdict
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


# --- Tournament Helper Utilities ---

def fetch_participants(conn, tournament_id):
    """Return a list of member IDs participating in the tournament."""
    rows = conn.execute(
        'SELECT member_id FROM tournament_participants WHERE tournament_id = ? ORDER BY member_id',
        (tournament_id,),
    ).fetchall()
    return [row['member_id'] for row in rows]


def fetch_members_by_ids(conn, member_ids):
    """Return a mapping of member_id -> member row for the given IDs."""
    if not member_ids:
        return {}
    placeholders = ','.join(['?'] * len(member_ids))
    rows = conn.execute(
        f'SELECT * FROM members WHERE id IN ({placeholders})',
        member_ids,
    ).fetchall()
    return {row['id']: row for row in rows}


def get_all_fixtures(conn, tournament_id):
    """Fetch all fixtures for a tournament, joined with player names."""
    return conn.execute(
        '''
        SELECT f.*, m1.name AS player1_name, m2.name AS player2_name
        FROM fixtures f
        JOIN members m1 ON f.player1_id = m1.id
        LEFT JOIN members m2 ON f.player2_id = m2.id
        WHERE f.tournament_id = ?
        ORDER BY f.round, f.id
        ''',
        (tournament_id,),
    ).fetchall()


def build_round_robin_schedule(participants, members):
    """Generate a full round-robin schedule as a list of rounds with pairings."""
    if not participants:
        return []
    def seed_key(pid):
        member = members.get(pid)
        rating = member['rating'] if member and member['rating'] is not None else 0
        name = member['name'] if member else str(pid)
        return (-rating, name)

    players = sorted(participants, key=seed_key)
    if len(players) % 2 == 1:
        players.append(None)
    n = len(players)
    rounds = n - 1
    schedule = []
    for _ in range(rounds):
        pairings = []
        for i in range(n // 2):
            p1 = players[i]
            p2 = players[n - 1 - i]
            if p1 is not None and p2 is not None:
                pairings.append((p1, p2))
            else:
                bye_player = p1 if p1 is not None else p2
                if bye_player is not None:
                    pairings.append((bye_player, None))
        schedule.append(pairings)
        # Rotate the players (keeping first player fixed)
        players = [players[0]] + [players[-1]] + players[1:-1]
    return schedule


def build_initial_swiss_pairings(participants, members):
    """Swiss round one: pair by rating (top half vs bottom half)."""
    def seed_key(pid):
        member = members.get(pid)
        rating = member['rating'] if member and member['rating'] is not None else 0
        name = member['name'] if member else str(pid)
        return (-rating, name)

    sorted_participants = sorted(participants, key=seed_key)
    mid = len(sorted_participants) // 2
    top = sorted_participants[:mid]
    bottom = sorted_participants[mid:]
    pairings = []
    for i in range(min(len(top), len(bottom))):
        pairings.append((top[i], bottom[i]))
    if len(sorted_participants) % 2 == 1:
        pairings.append((bottom[-1], None))
    return pairings


def compile_history_and_standings(participants, fixtures, members):
    """Compute per-player standings and opponent history from fixtures."""
    standings = {}
    history = defaultdict(set)
    for pid in participants:
        standings[pid] = {
            'score': 0.0,
            'wins': 0,
            'losses': 0,
            'draws': 0,
            'byes': 0,
            'played': 0,
            'had_bye': False,
        }

    for fixture in fixtures:
        p1 = fixture['player1_id']
        p2 = fixture['player2_id']
        result = fixture['result']
        if p2 is None:
            standings[p1]['score'] += 1
            standings[p1]['byes'] += 1
            standings[p1]['played'] += 1
            standings[p1]['had_bye'] = True
            continue
        history[p1].add(p2)
        history[p2].add(p1)
        if result == 'TBD':
            continue
        if result == '1-0':
            standings[p1]['score'] += 1
            standings[p1]['wins'] += 1
            standings[p2]['losses'] += 1
        elif result == '0-1':
            standings[p2]['score'] += 1
            standings[p2]['wins'] += 1
            standings[p1]['losses'] += 1
        elif result == '0.5-0.5':
            standings[p1]['score'] += 0.5
            standings[p2]['score'] += 0.5
            standings[p1]['draws'] += 1
            standings[p2]['draws'] += 1
        standings[p1]['played'] += 1
        standings[p2]['played'] += 1

    # Ensure every participant has a history entry
    for pid in participants:
        history[pid] = history.get(pid, set())

    ordered_rows = []
    for pid in participants:
        member = members.get(pid)
        name = member['name'] if member else 'Unknown player'
        rating = member['rating'] if member and member['rating'] is not None else None
        rating_for_sort = rating if rating is not None else 0
        ordered_rows.append(
            {
                'member_id': pid,
                'player_name': name,
                'player_rating': rating,
                'rating_for_sort': rating_for_sort,
                'score': standings[pid]['score'],
                'wins': standings[pid]['wins'],
                'losses': standings[pid]['losses'],
                'draws': standings[pid]['draws'],
                'played': standings[pid]['played'],
                'byes': standings[pid]['byes'],
            }
        )

    ordered = sorted(
        ordered_rows,
        key=lambda row: (
            -row['score'],
            -row['wins'],
            -row['rating_for_sort'],
            row['player_name'],
        ),
    )
    return standings, history, ordered


def swiss_next_round_pairings(participants, standings, history, members):
    """Generate Swiss pairings based on current standings and history."""
    players = participants[:]
    # Sort by score, then rating, then name for deterministic pairing
    def swiss_key(pid):
        member = members.get(pid)
        rating = member['rating'] if member and member['rating'] is not None else 0
        name = member['name'] if member else str(pid)
        return (-standings[pid]['score'], -rating, name)

    players.sort(key=swiss_key)

    bye_player = None
    if len(players) % 2 == 1:
        # Choose the lowest-ranked player without a bye yet
        for pid in reversed(players):
            if not standings[pid]['had_bye']:
                bye_player = pid
                break
        if bye_player is None:
            bye_player = players[-1]
        players.remove(bye_player)

    def backtrack(remaining, current):
        if not remaining:
            return current
        first = remaining[0]
        for idx in range(1, len(remaining)):
            opponent = remaining[idx]
            if opponent not in history[first]:
                new_remaining = remaining[1:idx] + remaining[idx + 1 :]
                res = backtrack(new_remaining, current + [(first, opponent)])
                if res is not None:
                    return res
        return None

    pairings = backtrack(players, [])
    if pairings is None:
        # Allow rematches as a fallback if unique pairing impossible
        pairings = []
        temp = players[:]
        while temp:
            p1 = temp.pop(0)
            p2 = temp.pop(0)
            pairings.append((p1, p2))

    if bye_player is not None:
        pairings.append((bye_player, None))

    return pairings


def knockout_pairings_from_players(player_ids):
    """Pair players sequentially for knockout play."""
    pairings = []
    for i in range(0, len(player_ids) - 1, 2):
        pairings.append((player_ids[i], player_ids[i + 1]))
    if len(player_ids) % 2 == 1:
        pairings.append((player_ids[-1], None))
    return pairings

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

        fixtures = get_all_fixtures(conn, tournament_id)
        participants = list(selected_ids)
        member_map = fetch_members_by_ids(conn, participants)
        standings_raw, history, standings_table = compile_history_and_standings(participants, fixtures, member_map)

        fixtures_by_round = defaultdict(list)
        for fixture in fixtures:
            fixtures_by_round[fixture['round']].append(fixture)
        max_round = max(fixtures_by_round.keys(), default=0)
        round_numbers = sorted(fixtures_by_round.keys())

        generate_disabled_reason = None
        can_generate = True
        generate_label = 'Generate Round 1'
        if not participants:
            can_generate = False
            generate_disabled_reason = 'Add participants before generating fixtures.'
        else:
            if max_round == 0:
                generate_label = 'Generate Round 1'
            else:
                generate_label = 'Generate Next Round'
                unfinished = conn.execute(
                    'SELECT COUNT(*) FROM fixtures WHERE tournament_id = ? AND round = ? AND result = "TBD"',
                    (tournament_id, max_round),
                ).fetchone()[0]
                if unfinished:
                    can_generate = False
                    generate_disabled_reason = 'Complete all results in the current round first.'
            if tournament['format'] == 'Round-robin' and fixtures:
                can_generate = False
                generate_disabled_reason = 'Round-robin schedules are generated in full.'

        all_results_recorded = fixtures and all(f['result'] != 'TBD' for f in fixtures)
        tournament_complete = False
        if tournament['format'] == 'Round-robin' and participants:
            expected_rounds = len(participants) if len(participants) % 2 == 1 else max(len(participants) - 1, 1)
            if fixtures and max_round >= expected_rounds and all_results_recorded:
                tournament_complete = True
        elif tournament['format'] == 'Swiss':
            if fixtures and all_results_recorded and participants and all(len(history[pid]) >= len(participants) - 1 for pid in participants):
                tournament_complete = True
        elif tournament['format'] == 'Knockout' and max_round:
            winners = []
            for fixture in sorted(fixtures_by_round[max_round], key=lambda f: f['id']):
                if fixture['player2_id'] is None:
                    winners.append(fixture['player1_id'])
                elif fixture['result'] == '1-0':
                    winners.append(fixture['player1_id'])
                elif fixture['result'] == '0-1':
                    winners.append(fixture['player2_id'])
            tournament_complete = len(winners) == 1 and all_results_recorded

        if tournament_complete:
            can_generate = False
            if not generate_disabled_reason:
                generate_disabled_reason = 'Tournament complete.'

    return render_template(
        'edit-tournament.html',
        tournament=tournament,
        members=members,
        selected_ids=selected_ids,
        fixtures_by_round=fixtures_by_round,
        round_numbers=round_numbers,
        standings=standings_table,
        can_generate=can_generate,
        generate_label=generate_label,
        generate_disabled_reason=generate_disabled_reason,
        tournament_complete=tournament_complete,
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
        try:
            conn.execute('DELETE FROM members WHERE id = ?', (member_id,))
            conn.commit()
            flash('Member deleted', 'success')
        except sqlite3.IntegrityError:
            conn.rollback()
            flash('Cannot delete member while they are assigned to tournaments. Remove them from fixtures first.',
                  'danger')
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
    """Generate fixtures for the next round of the tournament."""
    with get_db_connection() as conn:
        tournament = conn.execute('SELECT * FROM tournaments WHERE id = ?', (tournament_id,)).fetchone()
        if not tournament:
            flash('Tournament not found', 'danger')
            return redirect(url_for('index'))

        participants = fetch_participants(conn, tournament_id)
        if len(participants) < 2:
            flash('At least 2 participants required to generate fixtures', 'danger')
            return redirect(url_for('edit_tournament', tournament_id=tournament_id, _anchor='participants'))

        member_map = fetch_members_by_ids(conn, participants)
        fixtures = get_all_fixtures(conn, tournament_id)
        fixtures_by_round = defaultdict(list)
        for fixture in fixtures:
            fixtures_by_round[fixture['round']].append(fixture)
        current_round = max(fixtures_by_round.keys(), default=0)

        if current_round:
            unfinished = conn.execute(
                'SELECT COUNT(*) FROM fixtures WHERE tournament_id = ? AND round = ? AND result = "TBD"',
                (tournament_id, current_round),
            ).fetchone()[0]
            if unfinished:
                flash('Complete all results in the current round first.', 'danger')
                return redirect(url_for('edit_tournament', tournament_id=tournament_id, _anchor='fixtures'))

        format_ = tournament['format']

        # Determine pairings for the next round
        if current_round == 0:
            next_round = 1
            if format_ == 'Round-robin':
                schedule = build_round_robin_schedule(participants, member_map)
                for round_number, pairings in enumerate(schedule, start=1):
                    for p1, p2 in pairings:
                        result = '1-0' if p2 is None else 'TBD'
                        conn.execute(
                            'INSERT INTO fixtures (tournament_id, round, player1_id, player2_id, result) VALUES (?, ?, ?, ?, ?)',
                            (tournament_id, round_number, p1, p2, result),
                        )
                conn.commit()
                flash('Full round-robin schedule generated.', 'success')
                return redirect(url_for('edit_tournament', tournament_id=tournament_id, _anchor='fixtures'))
            elif format_ == 'Swiss':
                pairings = build_initial_swiss_pairings(participants, member_map)
            elif format_ == 'Knockout':
                # Seed by rating for deterministic brackets
                def knockout_seed_key(pid):
                    member = member_map.get(pid)
                    rating = member['rating'] if member and member['rating'] is not None else 0
                    name = member['name'] if member else str(pid)
                    return (-rating, name)

                seeded = sorted(participants, key=knockout_seed_key)
                pairings = knockout_pairings_from_players(seeded)
            else:
                flash('Unsupported tournament format.', 'danger')
                return redirect(url_for('edit_tournament', tournament_id=tournament_id))
        else:
            next_round = current_round + 1
            standings_raw, history, _ = compile_history_and_standings(participants, fixtures, member_map)
            if format_ == 'Swiss':
                # Check if all unique pairings exhausted
                if all(len(history[pid]) >= len(participants) - 1 for pid in participants):
                    flash('All players have faced each other. Swiss tournament complete.', 'info')
                    return redirect(url_for('edit_tournament', tournament_id=tournament_id, _anchor='fixtures'))
                pairings = swiss_next_round_pairings(participants, standings_raw, history, member_map)
            elif format_ == 'Knockout':
                previous_round = sorted(fixtures_by_round[current_round], key=lambda f: f['id'])
                winners = []
                for fixture in previous_round:
                    if fixture['player2_id'] is None:
                        winners.append(fixture['player1_id'])
                    elif fixture['result'] == '1-0':
                        winners.append(fixture['player1_id'])
                    elif fixture['result'] == '0-1':
                        winners.append(fixture['player2_id'])
                    else:
                        flash('Knockout fixtures must have a decisive result.', 'danger')
                        return redirect(url_for('edit_tournament', tournament_id=tournament_id, _anchor='fixtures'))
                if len(winners) <= 1:
                    flash('Tournament already has a winner.', 'info')
                    return redirect(url_for('edit_tournament', tournament_id=tournament_id, _anchor='fixtures'))
                pairings = knockout_pairings_from_players(winners)
            else:
                flash('Round-robin schedules are already generated in full.', 'info')
                return redirect(url_for('edit_tournament', tournament_id=tournament_id, _anchor='fixtures'))

        # Save fixtures for this round
        for p1, p2 in pairings:
            result = '1-0' if p2 is None else 'TBD'
            conn.execute(
                'INSERT INTO fixtures (tournament_id, round, player1_id, player2_id, result) VALUES (?, ?, ?, ?, ?)',
                (tournament_id, next_round, p1, p2, result),
            )
        conn.commit()

        if format_ == 'Knockout' and len(pairings) == 1 and pairings[0][1] is None:
            flash('Bye applied. Player advances automatically.', 'success')
        else:
            flash(f'Fixtures generated for round {next_round}.', 'success')

    return redirect(url_for('edit_tournament', tournament_id=tournament_id, _anchor='fixtures'))


@app.route('/fixture/<int:fixture_id>/update', methods=['POST'])
@login_required
def update_fixture_result(fixture_id):
    """Persist an updated result for a specific fixture."""
    desired_result = request.form.get('result')
    if desired_result not in {'TBD', '1-0', '0-1', '0.5-0.5'}:
        flash('Invalid result value provided.', 'danger')
        return redirect(request.referrer or url_for('index'))

    with get_db_connection() as conn:
        fixture = conn.execute(
            '''
            SELECT f.*, t.format
            FROM fixtures f
            JOIN tournaments t ON f.tournament_id = t.id
            WHERE f.id = ?
            ''',
            (fixture_id,),
        ).fetchone()
        if not fixture:
            flash('Fixture not found.', 'danger')
            return redirect(url_for('index'))

        if fixture['player2_id'] is None:
            flash('Bye fixtures are automatically scored and cannot be edited.', 'info')
            return redirect(url_for('edit_tournament', tournament_id=fixture['tournament_id'], _anchor='fixtures'))

        if fixture['format'] == 'Knockout' and desired_result == '0.5-0.5':
            flash('Knockout fixtures require a decisive result.', 'danger')
            return redirect(url_for('edit_tournament', tournament_id=fixture['tournament_id'], _anchor='fixtures'))

        conn.execute('UPDATE fixtures SET result = ? WHERE id = ?', (desired_result, fixture_id))
        conn.commit()

    flash('Fixture result updated.', 'success')
    return redirect(url_for('edit_tournament', tournament_id=fixture['tournament_id'], _anchor='fixtures'))

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
    """Export the full fixture list for a tournament as CSV."""
    import csv
    from io import StringIO

    with get_db_connection() as conn:
        fixtures = conn.execute(
            '''
            SELECT f.id, f.round, m1.name AS player1_name, m2.name AS player2_name, f.result
            FROM fixtures f
            JOIN members m1 ON f.player1_id = m1.id
            LEFT JOIN members m2 ON f.player2_id = m2.id
            WHERE f.tournament_id = ?
            ORDER BY f.round, f.id
            ''',
            (tournament_id,),
        ).fetchall()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Fixture ID', 'Round', 'Player 1', 'Player 2', 'Result'])
    for fixture in fixtures:
        writer.writerow([
            fixture['id'],
            fixture['round'],
            fixture['player1_name'],
            fixture['player2_name'] if fixture['player2_name'] else 'BYE',
            fixture['result'],
        ])

    output = si.getvalue()
    from flask import Response

    filename = f'tournament_{tournament_id}_fixtures.csv'
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
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
