from flask import Blueprint, render_template, request, redirect, session, flash
from db import execute_read, execute_query
from utils import login_required, role_required, get_branch_filter, get_active_branch_id

consignment_bp = Blueprint('consignment_bp', __name__)

@consignment_bp.route("/consignments")
@login_required
@role_required('admin', 'manager', 'accountant')
def consignments():
    try:
        b_filter, params = get_branch_filter(prefix=" WHERE c.")
        
        consignments_data = execute_read(f'''
            SELECT 
                c.Consignments_id AS id, 
                c.Sender_name AS sender, 
                c.Receiver_name AS receiver, 
                CONCAT(t.Route_From, " to ", t.Route_To) AS route, 
                c.Weight_tone AS weight,
                c.status AS status
            FROM consignments c
            LEFT JOIN trips t ON c.trip_id = t.Trip_id
            {b_filter}
        ''', params)
    except Exception as e:
        flash(f"Error loading consignments: {str(e)}", "error")
        consignments_data = []
    return render_template("consignments.html", consignments=consignments_data)

@consignment_bp.route("/add_consignment", methods=["GET", "POST"])
@login_required
@role_required('manager')
def add_consignment():
    if request.method == "POST":
        trip_id = request.form.get("trip_id")
        if not trip_id or trip_id.strip() == "":
            trip_id = None
            
        sender = request.form.get("sender")
        receiver = request.form.get("receiver")
        goods_type = request.form.get("goods_type")
        weight = request.form.get("weight")
        amount = request.form.get("amount")
        status = request.form.get("status", "booked")

        try:
            weight_val = float(weight) if weight else 0
            if weight_val <= 0:
                flash("Weight must be greater than zero.", "error")
                return redirect("/add_consignment")
                
            weight_tonnes = weight_val / 1000.0
            
            query = "INSERT INTO consignments(trip_id, Sender_name, Receiver_name, Goods_type, Weight_tone, Freight_Amount, status, branch_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)"
            execute_query(query,(trip_id, sender, receiver, goods_type, weight_tonnes, amount, status, get_active_branch_id()))
            flash("Consignment added successfully", "success")
        except Exception as e:
            flash(f"Error adding consignment: {str(e)}", "error")
        return redirect("/consignments")

    try:
        b_filter, params = get_branch_filter(prefix=" WHERE ")
        trips = execute_read(f"SELECT * FROM trips{b_filter}", params)
    except Exception as e:
        flash(f"Error loading trips: {str(e)}", "error")
        trips = []
    return render_template("add_consignment.html", trips=trips)

@consignment_bp.route("/edit_consignment/<id>", methods=["GET", "POST"])
@login_required
@role_required('manager')
def edit_consignment(id):
    if request.method == "POST":
        trip_id = request.form.get("trip_id")
        if not trip_id or trip_id.strip() == "":
            trip_id = None
            
        sender = request.form.get("sender")
        receiver = request.form.get("receiver")
        goods_type = request.form.get("goods_type")
        weight = request.form.get("weight")
        amount = request.form.get("amount")
        status = request.form.get("status")

        try:
            weight_val = float(weight) if weight else 0
            if weight_val <= 0:
                flash("Weight must be greater than zero.", "error")
                return redirect(f"/edit_consignment/{id}")
                
            weight_tonnes = weight_val / 1000.0
            
            b_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
            params = (trip_id, sender, receiver, goods_type, weight_tonnes, amount, status, id)
            if session.get('role') == 'manager':
                params += (session.get('branch_id'),)
                
            execute_query(f"UPDATE consignments SET trip_id=%s, Sender_name=%s, Receiver_name=%s, Goods_type=%s, Weight_tone=%s, Freight_Amount=%s, status=%s WHERE Consignments_id=%s{b_filter}", params)
            flash("Consignment updated successfully", "success")
            return redirect("/consignments")
        except Exception as e:
            flash(f"Error updating consignment: {str(e)}", "error")
            return redirect(f"/edit_consignment/{id}")

    try:
        b_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
        params = (id,)
        if session.get('role') == 'manager':
            params += (session.get('branch_id'),)
            
        consignment = execute_read(f"SELECT * FROM consignments WHERE Consignments_id=%s{b_filter}", params, fetchall=False)
        if not consignment:
            flash("Consignment not found or access denied.", "error")
            return redirect("/consignments")

        t_filter, t_params = get_branch_filter(prefix=" WHERE ")
        trips = execute_read(f"SELECT * FROM trips{t_filter}", t_params)
    except Exception as e:
        flash(f"Error loading consignment: {str(e)}", "error")
        return redirect("/consignments")

    return render_template("edit_consignment.html", consignment=consignment, trips=trips)

@consignment_bp.route("/delete_consignment/<id>")
@login_required
@role_required('manager')
def delete_consignment(id):
    try:
        b_filter = " AND branch_id = %s" if session.get('role') == 'manager' else ""
        params = (id,)
        if session.get('role') == 'manager':
            params += (session.get('branch_id'),)
            
        execute_query(f"DELETE FROM consignments WHERE Consignments_id=%s{b_filter}", params)
        flash("Consignment deleted successfully", "success")
    except Exception as e:
        flash(f"Error deleting consignment: {str(e)}", "error")
    return redirect("/consignments")
