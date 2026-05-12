import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, session, flash
from db import dbconnect, execute_read, execute_query, verify_database_schema
from utils import login_required, role_required, get_branch_filter
from routes.user_routes import user_bp
from routes.booking_routes import booking_bp
from routes.trip_routes import trip_bp
from routes.consignment_routes import consignment_bp
from routes.payment_routes import payment_bp
from routes.branch_routes import branch_bp

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads/profiles'
app.secret_key = "tms_secret_key"

app.register_blueprint(user_bp)
app.register_blueprint(booking_bp)
app.register_blueprint(trip_bp)
app.register_blueprint(consignment_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(branch_bp)


# -----------------------------
# LOGIN PAGE
# -----------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        logger.info(f"Login attempt - Email: {email}")

        conn = None
        cur = None
        try:
            conn = dbconnect()
            cur = conn.cursor(dictionary=True)

            # INFER ROLE DIRECTLY FROM DATABASE
            query = "SELECT * FROM users WHERE Email=%s"
            cur.execute(query, (email,))
            user = cur.fetchone()

            if user:
                logger.info(f"User found: {email}")
                
                # PASSWORD VERIFICATION
                password_valid = False
                
                if user["Password"].startswith("scrypt:") or user["Password"].startswith("pbkdf2:"):
                    password_valid = check_password_hash(user["Password"], password)
                else:
                    # Legacy plaintext passwords fallback
                    if user["Password"] == password:
                        password_valid = True
                        # Auto-upgrade plaintext password to hashed password
                        hashed_pw = generate_password_hash(password)
                        cur.execute("UPDATE users SET Password=%s WHERE user_id=%s", (hashed_pw, user["user_id"]))
                        conn.commit()

                if password_valid:
                    logger.info(f"Password matched for user: {email}")
                    
                    # SESSION CONSISTENCY
                    session["user_id"] = user["user_id"]
                    session["username"] = user["First_name"] + " " + user["Last_name"]
                    session["role"] = str(user["Role"]).lower()
                    session["branch_id"] = user.get("branch_id")
                    
                    if user.get("Profile_pic"):
                        session["profile_pic"] = user["Profile_pic"]

                    flash("Login successful!", "success")
                    if session["role"] == "customer":
                        return redirect("/my_bookings")
                    return redirect("/dashboard")
                else:
                    logger.warning(f"Password mismatch for user: {email}")
                    flash("Invalid Credentials", "error")
                    return render_template("login.html", error="Invalid Credentials")

            else:
                logger.warning(f"User not found for email: {email}")
                flash("User not found", "error")
                return render_template("login.html", error="User not found")

        except Exception as e:
            logger.error(f"Database error during login: {str(e)}")
            flash("An error occurred during login. Please try again.", "error")
            return render_template("login.html", error="Database error occurred.")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    return render_template("login.html")

# -----------------------------
# REGISTER
# -----------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password = request.form.get("password")
        phone = request.form.get("phone")

        try:
            existing_email = execute_read("SELECT * FROM users WHERE Email=%s", (email,), fetchall=False)
            if existing_email:
                flash("Email already registered. Please login.", "error")
                return redirect("/register")
                
            hashed_password = generate_password_hash(password)
            # Force role to customer
            query = "INSERT INTO users (First_name, Last_name, Email, Password, Role, Phone, Status) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            execute_query(query, (first_name, last_name, email, hashed_password, 'customer', phone, 'active'))
            
            flash("Registration successful! Please login.", "success")
            return redirect("/login")
        except Exception as e:
            flash(f"Error during registration: {str(e)}", "error")
            return redirect("/register")

    return render_template("register.html")

# -----------------------------
# LOGOUT
# -----------------------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -----------------------------
# DASHBOARD
# -----------------------------

@app.route("/set_branch_filter", methods=["POST"])
@login_required
@role_required('admin')
def set_branch_filter():
    branch_id = request.form.get("branch_id")
    session['admin_branch_filter'] = branch_id
    return redirect(request.referrer or "/dashboard")

@app.route("/dashboard")
@login_required
def dashboard():

    # CUSTOMER ROUTING
    if session.get("role") == "customer":
        return redirect("/my_bookings")

    try:
        # DRIVER DASHBOARD LOGIC
        if session.get("role") == "driver":
            # Fetch current trips
            current_trips = execute_read('''
                SELECT t.Trip_id AS id, v.Truck_Number AS truck, CONCAT(t.Route_From, " to ", t.Route_To) AS route, t.Start_Date AS start
                FROM trips t 
                LEFT JOIN vehicles v ON t.Vehicle_id = v.Vehicle_id
                WHERE t.Driver_id = %s AND t.trip_status IN ('Assigned', 'In Transit')
            ''', (session.get("user_id"),)) or []

            # Fetch upcoming trips
            upcoming_trips = execute_read('''
                SELECT t.Trip_id AS id, v.Truck_Number AS truck, CONCAT(t.Route_From, " to ", t.Route_To) AS route, t.Start_Date AS start
                FROM trips t 
                LEFT JOIN vehicles v ON t.Vehicle_id = v.Vehicle_id
                WHERE t.Driver_id = %s AND t.trip_status IN ('Pending', 'Approved')
            ''', (session.get("user_id"),)) or []

            return render_template("dashboard.html", current_trips=current_trips, upcoming_trips=upcoming_trips)


        # ADMIN / MANAGER / ACCOUNTANT LOGIC
        role = session.get("role")
        
        filter_clause_where, params_where = get_branch_filter(prefix=" WHERE ")
        filter_clause_and, params_and = get_branch_filter(prefix=" AND ")
        
        vehicle_count = (execute_read(f"SELECT COUNT(*) AS c FROM vehicles{filter_clause_where}", params_where, fetchall=False) or {}).get('c', 0)
        trip_count = (execute_read(f"SELECT COUNT(*) AS c FROM trips{filter_clause_where}", params_where, fetchall=False) or {}).get('c', 0)
        booking_count = (execute_read(f"SELECT COUNT(*) AS c FROM bookings{filter_clause_where}", params_where, fetchall=False) or {}).get('c', 0)
        
        available_drivers = (execute_read(f"SELECT COUNT(*) AS c FROM users WHERE Role='driver' AND Status='available'{filter_clause_and}", params_and, fetchall=False) or {}).get('c', 0)
        
        active_trips = (execute_read(f"SELECT COUNT(*) AS c FROM trips WHERE trip_status IN ('Assigned', 'In Transit'){filter_clause_and}", params_and, fetchall=False) or {}).get('c', 0)
        
        payment_total_row = execute_read(f"SELECT IFNULL(SUM(amount), 0) AS c FROM payments{filter_clause_where}", params_where, fetchall=False)
        payment_total = payment_total_row['c'] if payment_total_row else 0

        # --- REPORTING DATA FOR CHARTS --- #
        
        # 1. Revenue Report
        rev_today = float((execute_read(f"SELECT IFNULL(SUM(Amount), 0) AS c FROM payments WHERE Payment_date = CURDATE(){filter_clause_and}", params_and, fetchall=False) or {}).get('c', 0))
        rev_week = float((execute_read(f"SELECT IFNULL(SUM(Amount), 0) AS c FROM payments WHERE YEARWEEK(Payment_date, 1) = YEARWEEK(CURDATE(), 1){filter_clause_and}", params_and, fetchall=False) or {}).get('c', 0))
        rev_month = float((execute_read(f"SELECT IFNULL(SUM(Amount), 0) AS c FROM payments WHERE MONTH(Payment_date) = MONTH(CURDATE()) AND YEAR(Payment_date) = YEAR(CURDATE()){filter_clause_and}", params_and, fetchall=False) or {}).get('c', 0))
        rev_year = float((execute_read(f"SELECT IFNULL(SUM(Amount), 0) AS c FROM payments WHERE YEAR(Payment_date) = YEAR(CURDATE()){filter_clause_and}", params_and, fetchall=False) or {}).get('c', 0))
        revenue_data = [rev_today, rev_week, rev_month, rev_year]

        # 2. Trips Report
        trips_today = (execute_read(f"SELECT COUNT(*) AS c FROM trips WHERE Start_Date = CURDATE(){filter_clause_and}", params_and, fetchall=False) or {}).get('c', 0)
        trips_week = (execute_read(f"SELECT COUNT(*) AS c FROM trips WHERE YEARWEEK(Start_Date, 1) = YEARWEEK(CURDATE(), 1){filter_clause_and}", params_and, fetchall=False) or {}).get('c', 0)
        trips_month = (execute_read(f"SELECT COUNT(*) AS c FROM trips WHERE MONTH(Start_Date) = MONTH(CURDATE()) AND YEAR(Start_Date) = YEAR(CURDATE()){filter_clause_and}", params_and, fetchall=False) or {}).get('c', 0)
        trips_year = (execute_read(f"SELECT COUNT(*) AS c FROM trips WHERE YEAR(Start_Date) = YEAR(CURDATE()){filter_clause_and}", params_and, fetchall=False) or {}).get('c', 0)
        trips_data = [trips_today, trips_week, trips_month, trips_year]

        # 3. Vehicle Status
        v_stats_rows = execute_read(f"SELECT Status, COUNT(*) AS count FROM vehicles{filter_clause_where} GROUP BY Status", params_where) or []
        v_stats = {r['Status']: r['count'] for r in v_stats_rows}
        vehicle_data = [v_stats.get('available', 0), v_stats.get('in_use', 0), v_stats.get('maintenance', 0)]

        # 4. Booking Status
        b_stats_rows = execute_read(f"SELECT shipment_status, COUNT(*) AS count FROM bookings{filter_clause_where} GROUP BY shipment_status", params_where) or []
        b_stats = {r['shipment_status']: r['count'] for r in b_stats_rows}
        booking_data = [b_stats.get('Pending', 0), b_stats.get('Approved', 0), b_stats.get('In Transit', 0)]
        
        # 5. Managers & Branches
        total_branches = (execute_read("SELECT COUNT(*) AS c FROM branches", fetchall=False) or {}).get('c', 0) if role == 'admin' else 0
        total_managers = (execute_read(f"SELECT COUNT(*) AS c FROM users WHERE Role='manager'{filter_clause_and}", params_and, fetchall=False) or {}).get('c', 0) if role == 'admin' else 0
        
        branches_list = execute_read("SELECT * FROM branches") if role == 'admin' else []
        
        # 6. Branch Comparative Analytics (Only if 'All Branches' is selected)
        branch_comparisons = []
        if role == 'admin' and session.get('admin_branch_filter', 'all') == 'all':
            branch_comparisons = execute_read("""
                SELECT b.branch_name, 
                       (SELECT COUNT(*) FROM trips t WHERE t.branch_id = b.branch_id) as total_trips,
                       (SELECT IFNULL(SUM(amount), 0) FROM payments p WHERE p.branch_id = b.branch_id) as revenue
                FROM branches b
            """) or []
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f"Error loading dashboard: {str(e)}", "error")
        return render_template("dashboard.html", error="Dashboard data could not be loaded.",
            vehicle_count=0, trip_count=0, booking_count=0, available_drivers=0, active_trips=0, payment_total=0,
            revenue_data=[], trips_data=[], vehicle_data=[], booking_data=[], branches_list=[], branch_comparisons=[], total_branches=0, total_managers=0)

    return render_template(
        "dashboard.html",
        vehicle_count=vehicle_count,
        trip_count=trip_count,
        booking_count=booking_count,
        available_drivers=available_drivers,
        active_trips=active_trips,
        payment_total=payment_total,
        revenue_data=revenue_data,
        trips_data=trips_data,
        vehicle_data=vehicle_data,
        booking_data=booking_data,
        branches_list=branches_list,
        branch_comparisons=branch_comparisons,
        total_branches=total_branches,
        total_managers=total_managers
    )


# -----------------------------
# VEHICLES LIST
# -----------------------------
@app.route("/vehicles")
@login_required
def vehicles():

    try:
        filter_clause, params = get_branch_filter(prefix=" WHERE ")
        
        vehicles = execute_read(f'''
            SELECT 
                Vehicle_id AS id, 
                Registration_Number AS reg_no, 
                Capacity_Tons AS capacity, 
                Status AS status 
            FROM vehicles
            {filter_clause}
        ''', params)
    except Exception as e:
        flash(f"Error loading vehicles: {str(e)}", "error")
        vehicles = []

    return render_template("vehicles.html", vehicles=vehicles)


# -----------------------------
# ADD VEHICLE (POST)
# -----------------------------
@app.route("/add_vehicle", methods=["POST"])
@login_required
@role_required('manager')
def add_vehicle():

    truck_no = request.form.get("truck_no")
    reg_no = request.form.get("reg_no")
    capacity = request.form.get("capacity")
    status = request.form.get("status")

    print("DATA:", truck_no, reg_no, capacity, status)  # ✅ DEBUG

    # CHECK EMPTY VALUES (CRITICAL)
    if not truck_no or not reg_no or not capacity:
        flash("All fields are required", "error")
        return redirect("/add_vehicle")

    # ENUM VALID
    valid_status = ['available', 'in_use', 'maintenance', 'inactive']
    if status not in valid_status:
        status = 'available'

    try:
        float(capacity)
    except ValueError:
        flash("Capacity must be a number", "error")
        return redirect("/add_vehicle")

    try:
        # DUPLICATE TRUCK NUMBER
        existing_truck = execute_read("SELECT 1 FROM vehicles WHERE Truck_Number=%s", (truck_no,), fetchall=False)
        if existing_truck:
            flash("Truck number already exists", "error")
            return redirect("/add_vehicle")

        # DUPLICATE REG NO
        existing_reg = execute_read("SELECT 1 FROM vehicles WHERE Registration_Number=%s", (reg_no,), fetchall=False)
        if existing_reg:
            flash("Registration number already exists", "error")
            return redirect("/add_vehicle")

        # INSERT
        execute_query("""
            INSERT INTO vehicles
            (Truck_Number, Registration_Number, Capacity_Tons, Status, branch_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (truck_no, reg_no, capacity, status, session.get('branch_id')))

        flash("Vehicle added successfully", "success")

    except Exception as e:
        flash(f"Error: {str(e)}", "error")

    return redirect("/vehicles")


# -----------------------------
# EDIT VEHICLE
# -----------------------------
@app.route("/edit_vehicle/<int:id>", methods=["GET", "POST"])
@login_required
@role_required('manager')
def edit_vehicle(id):
    print("Edit called:", id)

    if request.method == "POST":

        reg_no = request.form.get("reg_no")
        capacity = request.form.get("capacity")
        status = request.form.get("status")

        # Validation
        try:
            float(capacity)
        except ValueError:
            flash("Capacity must be a number", "error")
            return redirect(f"/edit_vehicle/{id}")

        try:
            # Check duplicate (excluding current)
            existing_reg = execute_read("""
                SELECT 1 FROM vehicles 
                WHERE Registration_Number=%s AND Vehicle_id != %s
            """, (reg_no, id), fetchall=False)

            if existing_reg:
                flash("Registration number already exists", "error")
                return redirect(f"/edit_vehicle/{id}")

            # Update
            b_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
            params = (reg_no, capacity, status, id)
            if session.get('role') == 'manager':
                params += (session.get('branch_id'),)
                
            execute_query(f"""
                UPDATE vehicles 
                SET Registration_Number=%s, Capacity_Tons=%s, Status=%s 
                WHERE Vehicle_id=%s{b_filter}
            """, params)

            flash("Vehicle updated successfully", "success")
            return redirect("/vehicles")

        except Exception as e:
            flash(f"Error: {str(e)}", "error")
            return redirect(f"/edit_vehicle/{id}")

    # GET request
    try:
        b_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
        params = (id,)
        if session.get('role') == 'manager':
            params += (session.get('branch_id'),)
            
        vehicle = execute_read(f"SELECT * FROM vehicles WHERE Vehicle_id=%s{b_filter}", params, fetchall=False)
        if not vehicle:
            flash("Vehicle not found or access denied.", "error")
            return redirect("/vehicles")
    except Exception as e:
        flash(f"Error loading vehicle: {str(e)}", "error")
        return redirect("/vehicles")

    return render_template("edit_vehicle.html", vehicle=vehicle)


# -----------------------------
# DELETE VEHICLE
# -----------------------------
@app.route("/delete_vehicle/<int:id>", methods=["GET"])
@login_required
@role_required('manager')
def delete_vehicle(id):
    print("Delete called:", id)

    try:
        b_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
        params = (id,)
        if session.get('role') == 'manager':
            params += (session.get('branch_id'),)
            
        # Check if used in trips
        trip = execute_read("SELECT 1 FROM trips WHERE Vehicle_id=%s LIMIT 1", (id,), fetchall=False)

        if trip:
            # Soft delete
            execute_query(f"""
                UPDATE vehicles 
                SET Status='inactive' 
                WHERE Vehicle_id=%s{b_filter}
            """, params)
            flash("Vehicle is assigned to trips, marked as inactive", "warning")

        else:
            # Hard delete
            execute_query(f"DELETE FROM vehicles WHERE Vehicle_id=%s{b_filter}", params)
            flash("Vehicle deleted successfully", "success")

    except Exception as e:
        flash(f"Error: {str(e)}", "error")

    return redirect("/vehicles")


# -----------------------------
# ADD VEHICLE FORM (GET)
# -----------------------------
@app.route("/add_vehicle", methods=["GET"])
@login_required
@role_required('manager')
def add_vehicle_form():
    return render_template("add_vehicle.html")



# -----------------------------


# -----------------------------
# TRIPS
# -----------------------------



# -----------------------------
# PROFILE
# -----------------------------

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        import base64
        
        # Handle camera capture base64 upload
        if 'captured_image' in request.form and request.form['captured_image']:
            img_data = request.form['captured_image']
            if img_data.startswith('data:image'):
                img_data = img_data.split(',')[1]  # Remove data:image/png;base64,
                
            img_bytes = base64.b64decode(img_data)
            new_filename = f"user_{session.get('user_id')}_cam.png"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            
            with open(filepath, 'wb') as f:
                f.write(img_bytes)
                
            # Update database
            try:
                execute_query("UPDATE users SET Profile_pic=%s WHERE user_id=%s", (new_filename, session.get('user_id')))
                session['profile_pic'] = new_filename
                flash("Profile picture updated successfully!", "success")
            except Exception as e:
                flash(f"Database error updating profile: {e}", "error")
                
            return redirect("/profile")
            
        # Handle regular file upload
        elif 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                # Create unique filename
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                new_filename = f"user_{session.get('user_id')}.{ext}"
                
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                file.save(filepath)
                
                # Update database
                try:
                    execute_query("UPDATE users SET Profile_pic=%s WHERE user_id=%s", (new_filename, session.get('user_id')))
                    session['profile_pic'] = new_filename
                    flash("Profile picture updated successfully!", "success")
                except Exception as e:
                    flash(f"Database error updating profile: {e}", "error")
                    
                return redirect("/profile")

    try:
        user = execute_read("SELECT * FROM users WHERE user_id=%s", (session.get("user_id"),), fetchall=False)
    except Exception as e:
        flash("Error loading profile details.", "error")
        user = None
    
    # Store profile_pic in session if missing
    if user and user.get('Profile_pic'):
        session['profile_pic'] = user['Profile_pic']
        
    return render_template("profile.html", user=user)

# -----------------------------
# RUN SERVER
# -----------------------------

if __name__ == "__main__":
    verify_database_schema()
    app.run(debug=True)