from flask import Blueprint, render_template, request, redirect, session, flash, jsonify
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
                       (customer_id, pickup_location, drop_location, package_type, package_weight, delivery_date, contact_info, branch_id, booking_date) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURDATE())"""
            execute_query(query, (customer_id, pickup, drop, pkg_type, weight, date, contact, session.get('branch_id') or 1))
            flash("Booking created successfully!", "success")
            return redirect("/my_bookings")
        except Exception as e:
            flash(f"Error creating booking: {str(e)}", "error")
            return redirect("/book")
            
    return render_template("book.html")

@booking_bp.route("/customer_dashboard")
@login_required
@role_required('customer')
def customer_dashboard():
    customer_id = session.get("user_id")
    try:
        total_bookings = execute_read("SELECT COUNT(*) AS c FROM bookings WHERE customer_id=%s", (customer_id,), fetchall=False)['c']
        active_shipments = execute_read("SELECT COUNT(*) AS c FROM bookings WHERE customer_id=%s AND shipment_status IN ('Approved', 'In Transit', 'Out for Delivery')", (customer_id,), fetchall=False)['c']
        delivered_consignments = execute_read("SELECT COUNT(*) AS c FROM bookings WHERE customer_id=%s AND shipment_status = 'Delivered'", (customer_id,), fetchall=False)['c']
        
        pending_dues_row = execute_read("SELECT SUM(p.Amount) AS total FROM payments p JOIN bookings b ON p.Booking_id = b.booking_id WHERE b.customer_id=%s AND p.status='pending'", (customer_id,), fetchall=False)
        pending_dues = pending_dues_row['total'] if pending_dues_row and pending_dues_row['total'] else 0
        
        recent_bookings = execute_read("SELECT * FROM bookings WHERE customer_id=%s ORDER BY created_at DESC LIMIT 5", (customer_id,))
        
        return render_template("customer_dashboard.html", 
            total_bookings=total_bookings,
            active_shipments=active_shipments,
            delivered_consignments=delivered_consignments,
            pending_dues=pending_dues,
            recent_bookings=recent_bookings)
    except Exception as e:
        flash(f"Error loading dashboard: {str(e)}", "error")
        return redirect("/my_bookings")

@booking_bp.route("/api/estimate_pricing", methods=["POST"])
@login_required
@role_required('customer')
def estimate_pricing():
    data = request.json
    distance = data.get("distance", "local")
    try:
        weight = float(data.get("weight", 0))
    except (ValueError, TypeError):
        weight = 0
    priority = data.get("priority", "standard")
    fragile = data.get("fragile", False)
    
    base_charge = 300 if distance == "local" else 1200
    
    if priority == "express":
        base_charge *= 1.25
        
    handling_charge = 0
    if fragile:
        handling_charge = base_charge * 0.10
        
    extra_weight_charge = 0
    if weight > 50:
        extra_weight_charge = (weight - 50) * 15
        
    subtotal = base_charge + handling_charge + extra_weight_charge
    gst = subtotal * 0.18
    total = subtotal + gst
    
    return jsonify({
        "transport_charge": round(base_charge, 2),
        "handling_charge": round(handling_charge, 2),
        "extra_weight_charge": round(extra_weight_charge, 2),
        "subtotal": round(subtotal, 2),
        "gst": round(gst, 2),
        "total": round(total, 2)
    })

@booking_bp.route("/customer_pricing")
@login_required
@role_required('customer')
def customer_pricing():
    return render_template("customer_pricing.html")

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
