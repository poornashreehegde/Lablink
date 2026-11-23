import secrets
from functools import wraps
from flask import session, request, redirect, url_for, flash, abort, g
from models import User

def login_user(user):
    """Logs the user into the session."""
    session.clear()
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    session['full_name'] = user.full_name
    session['_csrf_token'] = secrets.token_hex(32)
    session.permanent = True

def logout_user():
    """Logs the user out and clears session."""
    session.clear()

def get_current_user():
    """Retrieves the currently authenticated user or None."""
    if 'user_id' not in session:
        return None
    if not hasattr(g, '_current_user') or g._current_user is None:
        g._current_user = User.query.get(session['user_id'])
    return g._current_user

def login_required(f):
    """Decorator to protect routes requiring authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """Decorator to restrict access to specific roles (e.g. 'admin', 'faculty')."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if user is None:
                flash("Please sign in to access this page.", "warning")
                return redirect(url_for('login', next=request.path))
            
            if user.role not in allowed_roles:
                flash("Access denied: You do not have permissions for this section.", "error")
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_csrf_token():
    """Generates or retrieves CSRF token for the session."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

def validate_csrf(token):
    """Validates provided CSRF token against session token."""
    session_token = session.get('_csrf_token')
    if not session_token or not token:
        return False
    return secrets.compare_digest(session_token, token)
