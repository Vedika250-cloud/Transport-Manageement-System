from flask import Blueprint, render_template, request, redirect, session, flash
from db import execute_read, execute_query
from utils import login_required, role_required, get_branch_filter

payment_bp = Blueprint('payment_bp', __name__)

@payment_bp.route("/payments")
@login_required
@role_required('admin', 'accountant', 'manager')
def payments():
    try:
        b_filter, params = get_branch_filter(prefix=" WHERE p.")
        
        payments_data = execute_read(f'''
            SELECT 
                p.Payment_id AS payment_id, 
                p.Amount AS amount, 
                p.method AS payment_method, 
                p.status AS status,
                p.Reference_no AS reference_no,
                p.Payment_date AS payment_date,
                c.trip_id AS trip_id,
                CONCAT(t.Route_From, ' to ', t.Route_To) AS trip
            FROM payments p
            LEFT JOIN consignments c ON p.Consignment_id = c.Consignments_id
            LEFT JOIN trips t ON c.trip_id = t.Trip_id
            {b_filter}
            ORDER BY p.Payment_id DESC
        ''', params)
        print("DEBUG PAYMENTS:", payments_data)
    except Exception as e:
        flash(f"Error loading payments: {str(e)}", "error")
        payments_data = []
    return render_template("payments.html", payments=payments_data)

@payment_bp.route("/add_payment", methods=["GET", "POST"])
@login_required
@role_required('accountant', 'manager')
def add_payment():
    if request.method == "POST":
        consignment_id = request.form.get("consignment_id")
        booking_id = request.form.get("booking_id")
        
        if not consignment_id or consignment_id.strip() == "":
            consignment_id = None
        if not booking_id or booking_id.strip() == "":
            booking_id = None

        amount = request.form.get("amount")
        payment_date = request.form.get("payment_date")
        payment_method = request.form.get("payment_method")
        reference_no = request.form.get("reference_no")
        status = request.form.get("status")

        try:
            query = "INSERT INTO payments(Consignment_id, Booking_id, Amount, Payment_date, method, Reference_no, status, branch_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)"
            execute_query(query,(consignment_id, booking_id, amount, payment_date, payment_method, reference_no, status, session.get('branch_id') or 1))
            flash("Payment added successfully", "success")
        except Exception as e:
            flash(f"Error adding payment: {str(e)}", "error")
        return redirect("/payments")

    try:
        b_filter = " WHERE branch_id = %s" if session.get('role') == 'manager' else ""
        params = (session.get('branch_id'),) if session.get('role') == 'manager' else ()
        consignments = execute_read(f"SELECT * FROM consignments{b_filter}", params)
        bookings = execute_read(f"SELECT * FROM bookings{b_filter}", params)
    except Exception as e:
        flash(f"Error loading data: {str(e)}", "error")
        consignments = []
        bookings = []
    return render_template("add_payment.html", consignments=consignments, bookings=bookings)

@payment_bp.route("/edit_payment/<id>", methods=["GET", "POST"])
@login_required
@role_required('accountant', 'manager')
def edit_payment(id):
    if request.method == "POST":
        consignment_id = request.form.get("consignment_id")
        booking_id = request.form.get("booking_id")
        
        if not consignment_id or consignment_id.strip() == "":
            consignment_id = None
        if not booking_id or booking_id.strip() == "":
            booking_id = None

        amount = request.form.get("amount")
        payment_date = request.form.get("payment_date")
        payment_method = request.form.get("payment_method")
        reference_no = request.form.get("reference_no")
        status = request.form.get("status")

        try:
            b_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
            params = (consignment_id, booking_id, amount, payment_date, payment_method, reference_no, status, id)
            if session.get('role') == 'manager':
                params += (session.get('branch_id'),)
                
            execute_query(f"UPDATE payments SET Consignment_id=%s, Booking_id=%s, Amount=%s, Payment_date=%s, method=%s, Reference_no=%s, status=%s WHERE Payment_id=%s{b_filter}", params)
            flash("Payment updated successfully", "success")
            return redirect("/payments")
        except Exception as e:
            flash(f"Error updating payment: {str(e)}", "error")
            return redirect(f"/edit_payment/{id}")

    try:
        b_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
        params = (id,)
        if session.get('role') == 'manager':
            params += (session.get('branch_id'),)
            
        payment = execute_read(f"SELECT * FROM payments WHERE Payment_id=%s{b_filter}", params, fetchall=False)
        if not payment:
            flash("Payment not found or access denied.", "error")
            return redirect("/payments")

        c_filter = " WHERE branch_id = %s" if session.get('role') == 'manager' else ""
        c_params = (session.get('branch_id'),) if session.get('role') == 'manager' else ()
        consignments = execute_read(f"SELECT * FROM consignments{c_filter}", c_params)
        bookings = execute_read(f"SELECT * FROM bookings{c_filter}", c_params)
    except Exception as e:
        flash(f"Error loading payment data: {str(e)}", "error")
        return redirect("/payments")

    return render_template("edit_payment.html", payment=payment, consignments=consignments, bookings=bookings)

@payment_bp.route("/delete_payment/<id>")
@login_required
@role_required('accountant', 'manager')
def delete_payment(id):
    try:
        b_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
        params = (id,)
        if session.get('role') == 'manager':
            params += (session.get('branch_id'),)
            
        execute_query(f"DELETE FROM payments WHERE Payment_id=%s{b_filter}", params)
        flash("Payment deleted successfully", "success")
    except Exception as e:
        flash(f"Error deleting payment: {str(e)}", "error")
    return redirect("/payments")
