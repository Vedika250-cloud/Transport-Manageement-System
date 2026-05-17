from functools import wraps
from flask import session, flash, redirect

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "error")
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)   
        def decorated_function(*args, **kwargs):
            if "role" not in session or session["role"] not in allowed_roles:
                flash("You do not have permission to access that feature.", "error")
                return redirect("/dashboard")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_branch_filter(prefix=" AND ", table_alias=""):
    """
    Returns (sql_clause, params_tuple) for branch filtering.
    For managers: strictly locked to their branch_id.
    For admins: uses session['admin_branch_filter'] if not 'all'.
    """
    col = f"{table_alias}.branch_id" if table_alias else "branch_id"
    role = session.get('role')
    
    if role == 'manager':
        return f"{prefix}{col} = %s", (session.get('branch_id'),)
    
    elif role == 'admin':
        admin_filter = session.get('admin_branch_filter', 'all')
        if admin_filter and admin_filter != 'all':
            return f"{prefix}{col} = %s", (admin_filter,)
            
    return "", ()

def get_active_branch_id():
    """
    Returns the branch_id that should be used for inserting new records.
    For admins, if they have an active branch filter, it uses that.
    Otherwise, defaults to the user's branch_id or 1 (Central Operations).
    """
    if session.get('role') == 'admin':
        admin_filter = session.get('admin_branch_filter', 'all')
        if admin_filter and admin_filter != 'all':
            return int(admin_filter)
    
    return session.get('branch_id') or 1
