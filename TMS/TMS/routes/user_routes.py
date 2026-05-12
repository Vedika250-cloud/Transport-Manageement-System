from flask import Blueprint, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash
from db import execute_read, execute_query
from utils import login_required, role_required, get_branch_filter

user_bp = Blueprint('user_bp', __name__)

# -----------------------------
# DRIVERS & USERS LISTING
# -----------------------------
@user_bp.route("/users")
@login_required
@role_required('admin', 'manager')
def users():
    user_type = request.args.get('type', 'driver') # default to driver

    # Managers cannot see other managers per user instruction
    if session.get('role') == 'manager' and user_type == 'manager':
        flash("You do not have permission to view management personnel.", "error")
        return redirect("/users?type=driver")

    try:
        data = []
        filter_clause, params = get_branch_filter(prefix=" AND ")

        if user_type == 'driver':
            data = execute_read(f"SELECT user_id AS id, CONCAT(First_name, ' ', Last_name) AS name, Email AS email, Phone AS phone, Status AS status FROM users WHERE Role='driver'{filter_clause}", params)
        elif user_type == 'manager':
            data = execute_read(f"SELECT user_id AS id, CONCAT(First_name, ' ', Last_name) AS name, Email AS email, Phone AS phone, Status AS status FROM users WHERE Role='manager'{filter_clause}", params)
        elif user_type == 'customer':
            data = execute_read(f"SELECT user_id AS id, CONCAT(First_name, ' ', Last_name) AS name, Email AS email, Phone AS phone, Status AS status FROM users WHERE Role='customer'{filter_clause}", params)
        elif user_type == 'accountant':
            data = execute_read(f"SELECT user_id AS id, CONCAT(First_name, ' ', Last_name) AS name, Email AS email, Phone AS phone, Status AS status FROM users WHERE Role='accountant'{filter_clause}", params)
    except Exception as e:
        flash(f"Error loading users: {str(e)}", "error")
        data = []

    return render_template("users.html", users_data=data, current_type=user_type)

@user_bp.route("/add_driver", methods=["GET", "POST"])
@login_required
@role_required('manager')
def add_driver():
    if request.method == "POST":
        name = request.form.get("name")
        license_number = request.form.get("license")
        phone = request.form.get("phone")
        status = request.form.get("status")

        if phone and not (phone.isdigit() and len(phone) == 10):
            flash("Phone number must contain exactly 10 digits.", "error")
            return redirect("/add_driver")

        try:
            # Check for existing user by phone
            if phone:
                existing_phone = execute_read("SELECT * FROM users WHERE Phone=%s AND Phone IS NOT NULL AND Phone != ''", (phone,), fetchall=False)
                if existing_phone:
                    flash("Driver with this phone number already exists.", "error")
                    return redirect("/add_driver")

            # We don't have a license_number field in users, but we can store it in a metadata table if needed.
            # Assuming 'license_number' was only in old 'drivers' table, we will just use the available 'users' table fields.
            # Using 'First_name' and 'Last_name' logic for the name field
            name_parts = name.split(" ", 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""
            
            # Since Email is required in users, we create a placeholder email if not provided
            placeholder_email = f"{first_name.lower()}.{last_name.lower()}@driver.local"
            
            existing_email = execute_read("SELECT * FROM users WHERE Email=%s", (placeholder_email,), fetchall=False)
            if existing_email:
                placeholder_email = f"{phone}@driver.local"

            hashed_password = generate_password_hash("driver123") # default password
            
            query = "INSERT INTO users(First_name, Last_name, Email, Password, Role, Phone, Status, branch_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)"
            execute_query(query,(first_name, last_name, placeholder_email, hashed_password, 'driver', phone, status, session.get('branch_id')))
            flash("Driver added successfully", "success")
        except Exception as e:
            flash(f"Error adding driver: {str(e)}", "error")

        return redirect("/users?type=driver")
        
    return render_template("add_driver.html")

@user_bp.route("/edit_driver/<id>", methods=["GET", "POST"])
@login_required
@role_required('manager')
def edit_driver(id):
    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        status = request.form.get("status")

        if phone and not (phone.isdigit() and len(phone) == 10):
            flash("Phone number must contain exactly 10 digits.", "error")
            return redirect(f"/edit_driver/{id}")

        try:
            if phone:
                existing_phone = execute_read("SELECT * FROM users WHERE Phone=%s AND Phone IS NOT NULL AND Phone != '' AND user_id != %s", (phone, id), fetchall=False)
                if existing_phone:
                    flash("Driver with this phone number already exists.", "error")
                    return redirect(f"/edit_driver/{id}")

            name_parts = name.split(" ", 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            b_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
            params = (first_name, last_name, phone, status, id)
            if session.get('role') == 'manager':
                params += (session.get('branch_id'),)

            execute_query(f"UPDATE users SET First_name=%s, Last_name=%s, Phone=%s, Status=%s WHERE user_id=%s{b_filter}", params)
            flash("Driver updated successfully", "success")
            return redirect("/users?type=driver")
        except Exception as e:
            flash(f"Error updating driver: {str(e)}", "error")
            return redirect(f"/edit_driver/{id}")

    try:
        b_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
        params = (id,)
        if session.get('role') == 'manager':
            params += (session.get('branch_id'),)
            
        driver = execute_read(f"SELECT user_id AS driver_id, CONCAT(First_name, ' ', Last_name) AS name, Phone AS phone, Status AS status FROM users WHERE user_id=%s{b_filter}", params, fetchall=False)
        if not driver:
            flash("Driver not found", "error")
            return redirect("/users?type=driver")
    except Exception as e:
        flash(f"Error loading driver: {str(e)}", "error")
        return redirect("/users?type=driver")

    return render_template("edit_driver.html", driver=driver)


@user_bp.route("/delete_driver/<id>")
@login_required
@role_required('manager')
def delete_driver(id):
    try:
        b_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
        params = (id,)
        if session.get('role') == 'manager':
            params += (session.get('branch_id'),)
            
        execute_query(f"DELETE FROM users WHERE user_id=%s AND Role='driver'{b_filter}", params)
        flash("Driver deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting driver: {str(e)}", "error")
    return redirect("/users?type=driver")

# -----------------------------
# SYSTEM USERS (MANAGERS/ACCOUNTANTS/CUSTOMERS)
# -----------------------------

@user_bp.route("/add_user", methods=["GET", "POST"])
@login_required
@role_required('admin')
def add_user():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password = request.form.get("password")
        phone = request.form.get("phone")
        role = request.form.get("role")
        status = request.form.get("status")
        branch_id = request.form.get("branch_id")
        if not branch_id or branch_id.strip() == "":
            branch_id = 1

        if role not in ['manager', 'accountant', 'customer']:
            flash("Invalid role selected.", "error")
            return redirect("/add_user")

        if phone and not (phone.isdigit() and len(phone) == 10):
            flash("Phone number must contain exactly 10 digits.", "error")
            return redirect("/add_user")

        try:
            # Check for duplicate email
            existing_email = execute_read("SELECT * FROM users WHERE Email=%s", (email,), fetchall=False)
            if existing_email:
                flash("User with this email already exists.", "error")
                return redirect("/add_user")
            
            if phone:
                existing_phone = execute_read("SELECT * FROM users WHERE Phone=%s AND Phone IS NOT NULL AND Phone != ''", (phone,), fetchall=False)
                if existing_phone:
                    flash("User with this phone number already exists.", "error")
                    return redirect("/add_user")

            hashed_password = generate_password_hash(password)
            query = "INSERT INTO users (First_name, Last_name, Email, Password, Role, Phone, Status, branch_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            execute_query(query, (first_name, last_name, email, hashed_password, role, phone, status, branch_id))
            flash(f"{role.capitalize()} added successfully", "success")
        except Exception as e:
            flash(f"Error adding user: {str(e)}", "error")
        return redirect(f"/users?type={role}")

    branches = execute_read("SELECT * FROM branches")
    return render_template("add_user.html", branches=branches)


@user_bp.route("/edit_user/<id>", methods=["GET", "POST"])
@login_required
@role_required('admin')
def edit_user(id):
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password_update = request.form.get("password")
        phone = request.form.get("phone")
        role = request.form.get("role")
        status = request.form.get("status")
        branch_id = request.form.get("branch_id")
        if not branch_id or branch_id.strip() == "":
            branch_id = 1

        if role not in ['manager', 'accountant', 'customer', 'driver']:
            flash("Invalid role selected.", "error")
            return redirect(f"/edit_user/{id}")

        if phone and not (phone.isdigit() and len(phone) == 10):
            flash("Phone number must contain exactly 10 digits.", "error")
            return redirect(f"/edit_user/{id}")

        try:
            existing_email = execute_read("SELECT * FROM users WHERE Email=%s AND User_id != %s", (email, id), fetchall=False)
            if existing_email:
                flash("User with this email already exists.", "error")
                return redirect(f"/edit_user/{id}")

            if phone:
                existing_phone = execute_read("SELECT * FROM users WHERE Phone=%s AND Phone IS NOT NULL AND Phone != '' AND User_id != %s", (phone, id), fetchall=False)
                if existing_phone:
                    flash("User with this phone number already exists.", "error")
                    return redirect(f"/edit_user/{id}")
            
            if password_update:
                hashed_password = generate_password_hash(password_update)
                execute_query("UPDATE users SET First_name=%s, Last_name=%s, Email=%s, Password=%s, Role=%s, Phone=%s, Status=%s, branch_id=%s WHERE User_id=%s",
                            (first_name, last_name, email, hashed_password, role, phone, status, branch_id, id))
            else:
                execute_query("UPDATE users SET First_name=%s, Last_name=%s, Email=%s, Role=%s, Phone=%s, Status=%s, branch_id=%s WHERE User_id=%s",
                            (first_name, last_name, email, role, phone, status, branch_id, id))
                
            flash(f"{role.capitalize()} updated successfully", "success")
            return redirect(f"/users?type={role}")
        except Exception as e:
            flash(f"Error updating user: {str(e)}", "error")
            return redirect(f"/edit_user/{id}")

    try:
        user_record = execute_read("SELECT * FROM users WHERE User_id=%s", (id,), fetchall=False)
        if not user_record:
            flash("User not found", "error")
            return redirect("/users?type=manager") 
        branches = execute_read("SELECT * FROM branches")
    except Exception as e:
        flash(f"Error loading user: {str(e)}", "error")
        return redirect("/users?type=manager")

    return render_template("edit_user.html", user=user_record, branches=branches)


@user_bp.route("/delete_user/<id>")
@login_required
@role_required('admin')
def delete_user(id):
    try:
        user_record = execute_read("SELECT Role FROM users WHERE User_id=%s", (id,), fetchall=False)
        
        if str(id) == str(session.get('user_id')):
            flash("You cannot delete your own admin account.", "error")
            return redirect("/dashboard")

        if user_record:
            role = user_record['Role']
            execute_query("DELETE FROM users WHERE User_id=%s", (id,))
            flash("User deleted successfully.", "success")
            return redirect(f"/users?type={role}")
            
    except Exception as e:
        flash(f"Error deleting user: {str(e)}", "error")
    
    return redirect("/users?type=manager")
