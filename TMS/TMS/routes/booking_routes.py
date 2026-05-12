from flask import Blueprint, render_template, request, redirect, session, flash
from db import execute_read, execute_query
from utils import login_required, role_required, get_branch_filter

booking_bp = Blueprint('booking_bp', __name__)

@booking_bp.route("/book", methods=["GET", "POST"])
@login_required
@role_required('customer')
def book_delivery():
    if request.method == "POST":
        pickup = request.form.get("pickup_location")
        drop = request.form.get("drop_location")
        pkg_type = request.form.get("package_type")
        weight = request.form.get("package_weight")
        date = request.form.get("delivery_date")
        contact = request.form.get("contact_info")
        
        customer_id = session.get("user_id")
        
        try:
            query = """INSERT INTO bookings 
                       (customer_id, pickup_location, drop_location, package_type, package_weight, delivery_date, contact_info, branch_id) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
            execute_query(query, (customer_id, pickup, drop, pkg_type, weight, date, contact, session.get('branch_id') or 1))
            flash("Booking created successfully!", "success")
            return redirect("/my_bookings")
        except Exception as e:
            flash(f"Error creating booking: {str(e)}", "error")
            return redirect("/book")
            
    return render_template("book.html")

@booking_bp.route("/my_bookings")
@login_required
@role_required('customer')
def my_bookings():
    customer_id = session.get("user_id")
    try:
        bookings = execute_read("SELECT * FROM bookings WHERE customer_id=%s ORDER BY created_at DESC", (customer_id,))
        return render_template("my_bookings.html", bookings=bookings)
    except Exception as e:
        flash(f"Error fetching bookings: {str(e)}", "error")
        return redirect("/dashboard")

@booking_bp.route("/manage_bookings")
@login_required
@role_required('admin', 'manager')
def manage_bookings():
    try:
        filter_clause, params = get_branch_filter(prefix=" WHERE ", table_alias="b")
        
        bookings = execute_read(f"""
            SELECT b.*, CONCAT(u.First_name, ' ', u.Last_name) as customer_name 
            FROM bookings b 
            JOIN users u ON b.customer_id = u.user_id 
            {filter_clause}
            ORDER BY b.created_at DESC
        """, params)
        return render_template("manage_bookings.html", bookings=bookings)
    except Exception as e:
        flash(f"Error fetching bookings: {str(e)}", "error")
        return redirect("/dashboard")

@booking_bp.route("/approve_booking/<int:id>")
@login_required
@role_required('manager')
def approve_booking(id):
    try:
        b_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
        params = (id,)
        if session.get('role') == 'manager':
            params += (session.get('branch_id'),)
            
        execute_query(f"UPDATE bookings SET shipment_status='Approved' WHERE booking_id=%s{b_filter}", params)
        flash("Booking approved successfully", "success")
    except Exception as e:
        flash(f"Error updating booking: {str(e)}", "error")
    return redirect("/manage_bookings")
