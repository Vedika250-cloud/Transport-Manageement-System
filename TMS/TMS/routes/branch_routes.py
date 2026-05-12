from flask import Blueprint, render_template, request, redirect, flash, session
from db import execute_read, execute_query
from utils import login_required, role_required

branch_bp = Blueprint('branch_bp', __name__)

@branch_bp.route("/branches")
@login_required
@role_required('admin')
def branches():
    try:
        branches_data = execute_read('''
            SELECT 
                b.branch_id, 
                b.branch_name, 
                b.city,
                b.state,
                GROUP_CONCAT(CONCAT(u.First_name, ' ', u.Last_name) SEPARATOR ', ') as manager_names,
                GROUP_CONCAT(u.Phone SEPARATOR ', ') as manager_phones,
                (SELECT COUNT(*) FROM users u2 WHERE u2.branch_id = b.branch_id AND u2.Role = 'driver') as driver_count,
                (SELECT COUNT(*) FROM vehicles v WHERE v.branch_id = b.branch_id) as vehicle_count
            FROM branches b
            LEFT JOIN users u ON u.branch_id = b.branch_id AND u.Role = 'manager'
            GROUP BY b.branch_id, b.branch_name, b.city, b.state
            ORDER BY b.branch_id ASC
        ''')
    except Exception as e:
        flash(f"Error loading branches: {str(e)}", "error")
        branches_data = []

    return render_template("branches.html", branches=branches_data)

@branch_bp.route("/add_branch", methods=["GET", "POST"])
@login_required
@role_required('admin')
def add_branch():
    if request.method == "POST":
        branch_name = request.form.get("branch_name")
        city = request.form.get("city")
        state = request.form.get("state")

        if not branch_name:
            flash("Branch name is required.", "error")
            return redirect("/add_branch")

        try:
            execute_query("""
                INSERT INTO branches (branch_name, city, state)
                VALUES (%s, %s, %s)
            """, (branch_name, city, state))
            flash("Branch added successfully.", "success")
            return redirect("/branches")
        except Exception as e:
            flash(f"Error adding branch: {str(e)}", "error")
            return redirect("/add_branch")

    return render_template("add_branch.html")

@branch_bp.route("/edit_branch/<int:id>", methods=["GET", "POST"])
@login_required
@role_required('admin')
def edit_branch(id):
    if request.method == "POST":
        branch_name = request.form.get("branch_name")
        city = request.form.get("city")
        state = request.form.get("state")

        if not branch_name:
            flash("Branch name is required.", "error")
            return redirect(f"/edit_branch/{id}")

        try:
            execute_query("""
                UPDATE branches 
                SET branch_name=%s, city=%s, state=%s 
                WHERE branch_id=%s
            """, (branch_name, city, state, id))
            flash("Branch updated successfully.", "success")
            return redirect("/branches")
        except Exception as e:
            flash(f"Error updating branch: {str(e)}", "error")
            return redirect(f"/edit_branch/{id}")

    try:
        branch = execute_read("SELECT * FROM branches WHERE branch_id=%s", (id,), fetchall=False)
        if not branch:
            flash("Branch not found.", "error")
            return redirect("/branches")
    except Exception as e:
        flash(f"Error loading branch: {str(e)}", "error")
        return redirect("/branches")

    return render_template("edit_branch.html", branch=branch)

@branch_bp.route("/delete_branch/<int:id>")
@login_required
@role_required('admin')
def delete_branch(id):
    if id == 1:
        flash("Cannot delete the Central Operations default branch.", "error")
        return redirect("/branches")
        
    try:
        # Reassign everything to Central Operations (id=1)
        execute_query("UPDATE users SET branch_id=1 WHERE branch_id=%s", (id,))
        execute_query("UPDATE vehicles SET branch_id=1 WHERE branch_id=%s", (id,))
        execute_query("UPDATE trips SET branch_id=1 WHERE branch_id=%s", (id,))
        execute_query("UPDATE bookings SET branch_id=1 WHERE branch_id=%s", (id,))
        execute_query("UPDATE consignments SET branch_id=1 WHERE branch_id=%s", (id,))
        execute_query("UPDATE payments SET branch_id=1 WHERE branch_id=%s", (id,))
        
        execute_query("DELETE FROM branches WHERE branch_id=%s", (id,))
        flash("Branch deleted. All associated records have been moved to Central Operations.", "success")
    except Exception as e:
        flash(f"Error deleting branch: {str(e)}", "error")
        
    return redirect("/branches")
