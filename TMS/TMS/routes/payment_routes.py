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

@payment_bp.route("/my_payments")
@login_required
@role_required('customer')
def my_payments():
    customer_id = session.get("user_id")
    try:
        payments_data = execute_read('''
            SELECT 
                p.Payment_id AS payment_id, 
                p.Amount AS amount, 
                p.advance_paid,
                p.remaining_amount,
                p.method AS payment_method, 
                p.status AS status,
                p.Reference_no AS reference_no,
                p.Payment_date AS payment_date,
                b.booking_id AS booking_id,
                b.pickup_location,
                b.drop_location
            FROM payments p
            JOIN bookings b ON p.Booking_id = b.booking_id
            WHERE b.customer_id = %s
            ORDER BY p.Payment_date DESC, p.Payment_id DESC
        ''', (customer_id,))
    except Exception as e:
        flash(f"Error loading your payments: {str(e)}", "error")
        payments_data = []
    return render_template("my_payments.html", payments=payments_data)

@payment_bp.route("/invoice/<int:payment_id>")
@login_required
@role_required('customer')
def invoice(payment_id):
    customer_id = session.get("user_id")
    try:
        payment = execute_read('''
            SELECT p.*, b.*, CONCAT(u.First_name, ' ', u.Last_name) as customer_name, u.Email, u.Phone
            FROM payments p
            JOIN bookings b ON p.Booking_id = b.booking_id
            JOIN users u ON b.customer_id = u.user_id
            WHERE p.Payment_id = %s AND b.customer_id = %s
        ''', (payment_id, customer_id), fetchall=False)
        
        if not payment:
            flash("Invoice not found or unauthorized.", "error")
            return redirect("/my_payments")
            
        payment['total_amount'] = float(payment['total_amount'])
        payment['advance_paid'] = float(payment['advance_paid'])
        payment['remaining_amount'] = float(payment['remaining_amount'])
            
        return render_template("invoice.html", payment=payment)
    except Exception as e:
        flash(f"Error loading invoice: {str(e)}", "error")
        return redirect("/my_payments")

@payment_bp.route("/mark_cod_completed/<int:payment_id>")
@login_required
@role_required('manager', 'admin')
def mark_cod_completed(payment_id):
    try:
        b_filter = " AND p.branch_id = %s" if session.get('role') == 'manager' else ""
        params = (payment_id,)
        if session.get('role') == 'manager':
            params += (session.get('branch_id'),)
            
        payment = execute_read(f"SELECT * FROM payments p WHERE p.Payment_id=%s{b_filter}", params, fetchall=False)
        if not payment or payment['status'] != 'COD Pending':
            flash("Invalid payment or already completed.", "error")
            return redirect("/payments")
            
        execute_query("UPDATE payments SET advance_paid=Amount, remaining_amount=0, status='Completed' WHERE Payment_id=%s", (payment_id,))
        if payment['Booking_id']:
            execute_query("UPDATE bookings SET advance_paid=total_amount, remaining_amount=0, shipment_status='Delivered' WHERE booking_id=%s", (payment['Booking_id'],))
            
        flash("COD Payment marked as Completed.", "success")
    except Exception as e:
        flash(f"Error updating payment: {str(e)}", "error")
    return redirect("/payments")
