from flask import Blueprint, render_template, request, redirect, session, flash
from db import execute_read, execute_query
from utils import login_required, role_required, get_branch_filter

trip_bp = Blueprint('trip_bp', __name__)

@trip_bp.route("/trips")
@login_required
def trips():
    try:
        b_filter, params = get_branch_filter(prefix=" WHERE t.")
        
        trips_data = execute_read(f'''
            SELECT 
                t.Trip_id AS id, 
                CONCAT(u.First_name, ' ', u.Last_name) AS driver, 
                v.Truck_Number AS truck, 
                CONCAT(t.Route_From, " to ", t.Route_To) AS route, 
                t.Status AS status 
            FROM trips t
            LEFT JOIN users u ON t.Driver_id = u.user_id AND u.Role = 'driver'
            LEFT JOIN vehicles v ON t.Vehicle_id = v.Vehicle_id
            {b_filter}
        ''', params)
    except Exception as e:
        flash(f"Error loading trips: {str(e)}", "error")
        trips_data = []
    return render_template("trips.html", trips=trips_data)

@trip_bp.route("/add_trip", methods=["GET", "POST"])
@login_required
@role_required('manager')
def add_trip():
    if request.method == "POST":
        vehicle_id = request.form.get("vehicle_id")
        driver_id = request.form.get("driver_id")
        route_from = request.form.get("route_from")
        route_to = request.form.get("route_to")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        status = request.form.get("status", "Pending")

        if end_date and start_date and start_date > end_date:
            flash("Start date must be before end date.", "error")
            return redirect("/add_trip")

        try:
            # Driver Validation
            existing_driver = execute_read("""
                SELECT 1 FROM trips 
                WHERE Driver_id=%s AND Start_Date=%s 
                AND Status IN ('Assigned', 'In Transit')
            """, (driver_id, start_date), fetchall=False)
            if existing_driver:
                flash("Driver already assigned to another trip on this date.", "error")
                return redirect("/add_trip")

            # Vehicle Validation
            existing_vehicle = execute_read("""
                SELECT 1 FROM trips 
                WHERE Vehicle_id=%s AND Start_Date=%s 
                AND Status IN ('Assigned', 'In Transit')
            """, (vehicle_id, start_date), fetchall=False)
            if existing_vehicle:
                flash("Vehicle already assigned to another trip on this date.", "error")
                return redirect("/add_trip")

            query = "INSERT INTO trips(Vehicle_id, Driver_id, Route_From, Route_To, Start_Date, End_Date, Status, branch_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)"
            execute_query(query,(vehicle_id, driver_id, route_from, route_to, start_date, end_date or None, status, session.get('branch_id')))
            flash("Trip added successfully", "success")
        except Exception as e:
            flash(f"Error adding trip: {str(e)}", "error")
        return redirect("/trips")
        
    try:
        b_filter = " WHERE branch_id = %s" if session.get('role') == 'manager' else ""
        d_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
        params = (session.get('branch_id'),) if session.get('role') == 'manager' else ()
        
        vehicles = execute_read(f"SELECT * FROM vehicles{b_filter}", params)
        drivers = execute_read(f"SELECT user_id AS driver_id, CONCAT(First_name, ' ', Last_name) AS name FROM users WHERE Role='driver' AND Status='active'{d_filter}", params)
    except Exception as e:
        flash(f"Error loading data: {str(e)}", "error")
        vehicles = []
        drivers = []
    return render_template("add_trip.html", vehicles=vehicles, drivers=drivers)

@trip_bp.route("/edit_trip/<id>", methods=["GET", "POST"])
@login_required
@role_required('manager')
def edit_trip(id):
    if request.method == "POST":
        vehicle_id = request.form.get("vehicle_id")
        driver_id = request.form.get("driver_id")
        route_from = request.form.get("route_from")
        route_to = request.form.get("route_to")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        status = request.form.get("status")

        if end_date and start_date and start_date > end_date:
            flash("Start date must be before end date.", "error")
            return redirect(f"/edit_trip/{id}")

        try:
            # Check for locking
            current_trip = execute_read("SELECT Status FROM trips WHERE Trip_id=%s", (id,), fetchall=False)
            if current_trip and current_trip['Status'] in ['Delivered', 'Cancelled'] and session.get('role') != 'admin':
                flash("This trip is locked and cannot be modified. Contact an administrator.", "error")
                return redirect("/trips")

            # Driver Validation
            existing_driver = execute_read("""
                SELECT 1 FROM trips 
                WHERE Driver_id=%s AND Start_Date=%s 
                AND Status IN ('Assigned', 'In Transit') AND Trip_id != %s
            """, (driver_id, start_date, id), fetchall=False)
            if existing_driver:
                flash("Driver already assigned to another trip on this date.", "error")
                return redirect(f"/edit_trip/{id}")

            # Vehicle Validation
            existing_vehicle = execute_read("""
                SELECT 1 FROM trips 
                WHERE Vehicle_id=%s AND Start_Date=%s 
                AND Status IN ('Assigned', 'In Transit') AND Trip_id != %s
            """, (vehicle_id, start_date, id), fetchall=False)
            if existing_vehicle:
                flash("Vehicle already assigned to another trip on this date.", "error")
                return redirect(f"/edit_trip/{id}")

            b_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
            params = (vehicle_id, driver_id, route_from, route_to, start_date, end_date or None, status, id)
            if session.get('role') == 'manager':
                params += (session.get('branch_id'),)
                
            execute_query(f"UPDATE trips SET Vehicle_id=%s, Driver_id=%s, Route_From=%s, Route_To=%s, Start_Date=%s, End_Date=%s, Status=%s WHERE Trip_id=%s{b_filter}", params)
            flash("Trip updated successfully", "success")
            return redirect("/trips")
        except Exception as e:
            flash(f"Error updating trip: {str(e)}", "error")
            return redirect(f"/edit_trip/{id}")

    try:
        b_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
        params = (id,)
        if session.get('role') == 'manager':
            params += (session.get('branch_id'),)
            
        trip = execute_read(f"SELECT * FROM trips WHERE Trip_id=%s{b_filter}", params, fetchall=False)
        if not trip:
            flash("Trip not found", "error")
            return redirect("/trips")

        if trip['Status'] in ['Delivered', 'Cancelled'] and session.get('role') != 'admin':
            flash("This trip is locked and cannot be edited.", "error")
            return redirect("/trips")

        b_filter = " WHERE branch_id = %s" if session.get('role') == 'manager' else ""
        d_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
        params_dd = (session.get('branch_id'),) if session.get('role') == 'manager' else ()
        
        drivers = execute_read(f"SELECT user_id AS driver_id, CONCAT(First_name, ' ', Last_name) AS name FROM users WHERE Role='driver' AND Status='active'{d_filter}", params_dd)
        vehicles = execute_read(f"SELECT * FROM vehicles{b_filter}", params_dd)
    except Exception as e:
        flash(f"Error loading trip data: {str(e)}", "error")
        return redirect("/trips")

    return render_template("edit_trip.html", trip=trip, drivers=drivers, vehicles=vehicles)

@trip_bp.route("/delete_trip/<id>")
@login_required
@role_required('manager')
def delete_trip(id):
    try:
        b_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
        params = (id,)
        if session.get('role') == 'manager':
            params += (session.get('branch_id'),)
            
        execute_query(f"DELETE FROM trips WHERE Trip_id=%s{b_filter}", params)
        flash("Trip deleted successfully", "success")
    except Exception as e:
        flash(f"Error deleting trip: {str(e)}", "error")
    return redirect("/trips")

@trip_bp.route("/update_trip_status/<id>", methods=["POST"])
@login_required
@role_required('driver', 'manager')
def update_trip_status(id):
    status = request.form.get("status")
    try:
        # Check locking
        current_trip = execute_read("SELECT Status, booking_id FROM trips WHERE Trip_id=%s", (id,), fetchall=False)
        if current_trip and current_trip['Status'] in ['Delivered', 'Cancelled'] and session.get('role') != 'admin':
            flash("This trip is locked. Status cannot be changed.", "error")
            return redirect("/trips")
            
        # Update trip status
        if session.get('role') == 'driver':
            execute_query("UPDATE trips SET Status=%s WHERE Trip_id=%s AND Driver_id=%s", (status, id, session.get('user_id')))
        elif session.get('role') == 'manager':
            execute_query("UPDATE trips SET Status=%s WHERE Trip_id=%s AND branch_id=%s", (status, id, session.get('branch_id')))
        else:
            execute_query("UPDATE trips SET Status=%s WHERE Trip_id=%s", (status, id))
        
        # If the trip is linked to a booking, update booking status too
        if current_trip and current_trip['booking_id']:
            execute_query("UPDATE bookings SET shipment_status=%s WHERE booking_id=%s", (status, current_trip['booking_id']))
            
        flash("Trip status updated successfully", "success")
    except Exception as e:
        flash(f"Error updating trip: {str(e)}", "error")
        
    # Redirect appropriately
    if session.get('role') == 'driver':
        return redirect("/dashboard")
    return redirect("/trips")
