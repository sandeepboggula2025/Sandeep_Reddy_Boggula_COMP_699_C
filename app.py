import os
from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory, Response
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from config import Config
from models import db, User, PickupRequest, ItemDetail, Notification
from forms import (LoginForm, HouseholdRegistrationForm, StaffRegistrationForm,
                   PickupRequestForm, ItemDetailForm, UpdateStatusForm)
from utils import hash_password, verify_password, allowed_file, ensure_upload_folder
from werkzeug.utils import secure_filename
import csv
from io import StringIO

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    ensure_upload_folder()
    db.init_app(app)
    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Create DB + admin user if not exists
    @app.before_first_request
    def create_all():
        db.create_all()
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@example.com', password_hash=hash_password('admin123'), role='admin', name='System Admin')
            db.session.add(admin)
            db.session.commit()

    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/register/household', methods=['GET','POST'])
    def register_household():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        form = HouseholdRegistrationForm()
        if form.validate_on_submit():
            if User.query.filter((User.username==form.username.data)|(User.email==form.email.data)).first():
                flash("Username or email already taken", "danger")
            else:
                user = User(
                    username=form.username.data,
                    email=form.email.data,
                    password_hash=hash_password(form.password.data),
                    role='household',
                    name=form.name.data,
                    address=form.address.data,
                    phone=form.phone.data
                )
                db.session.add(user)
                db.session.commit()
                flash("Registration successful. Please login.", "success")
                return redirect(url_for('login'))
        return render_template('register_household.html', form=form)

    @app.route('/register/staff', methods=['GET','POST'])
    def register_staff():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        form = StaffRegistrationForm()
        if form.validate_on_submit():
            if User.query.filter((User.username==form.username.data)|(User.email==form.email.data)).first():
                flash("Username or email already taken", "danger")
            else:
                user = User(
                    username=form.username.data,
                    email=form.email.data,
                    password_hash=hash_password(form.password.data),
                    role='staff',
                    name=form.name.data
                )
                db.session.add(user)
                db.session.commit()
                flash("Staff registration successful. You can login now.", "success")
                return redirect(url_for('login'))
        return render_template('register_staff.html', form=form)

    @app.route('/login', methods=['GET','POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        form = LoginForm()
        if form.validate_on_submit():
            identifier = form.username.data
            user = User.query.filter((User.username==identifier)|(User.email==identifier)).first()
            if user and verify_password(user.password_hash, form.password.data):
                login_user(user)
                flash("Login successful", "success")
                # redirect by role
                if user.is_admin():
                    return redirect(url_for('admin_dashboard'))
                if user.is_staff():
                    return redirect(url_for('staff_dashboard'))
                return redirect(url_for('household_dashboard'))
            else:
                flash("Invalid credentials", "danger")
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash("Logged out", "info")
        return redirect(url_for('home'))

    # Household dashboard
    @app.route('/household/dashboard')
    @login_required
    def household_dashboard():
        if not current_user.is_household():
            flash("Unauthorized", "danger")
            return redirect(url_for('home'))
        pickups = PickupRequest.query.filter_by(household_id=current_user.id).order_by(PickupRequest.created_at.desc()).all()
        notifications = Notification.query.filter_by(recipient_id=current_user.id).order_by(Notification.created_at.desc()).all()
        return render_template('household_dashboard.html', pickups=pickups, notifications=notifications)

    @app.route('/pickup/request', methods=['GET','POST'])
    @login_required
    def request_pickup():
        if not current_user.is_household():
            flash("Only households can request pickups", "danger")
            return redirect(url_for('home'))
        pr_form = PickupRequestForm()
        item_form = ItemDetailForm()
        if pr_form.validate_on_submit() and item_form.validate():
            filename = None
            file_field = request.files.get('photo')
            if file_field and file_field.filename != '' and allowed_file(file_field.filename):
                filename = secure_filename(file_field.filename)
                file_field.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            pickup = PickupRequest(
                household_id=current_user.id,
                location=pr_form.location.data,
                scheduled_date=pr_form.scheduled_date.data or None,
                notes=pr_form.notes.data,
                photo_filename=filename,
                status='pending'
            )
            db.session.add(pickup)
            db.session.commit()
            item = ItemDetail(
                request_id=pickup.id,
                item_type=item_form.item_type.data,
                quantity=item_form.quantity.data,
                condition_status=item_form.condition_status.data
            )
            db.session.add(item)
            db.session.commit()
            # create notification
            n = Notification(recipient_id=current_user.id, message=f"Pickup request #{pickup.id} submitted and pending admin approval.")
            db.session.add(n); db.session.commit()
            flash("Pickup request submitted. You will be notified when admin approves.", "success")
            return redirect(url_for('household_dashboard'))
        return render_template('request_pickup.html', pr_form=pr_form, item_form=item_form)

    @app.route('/pickup/<int:pid>')
    @login_required
    def pickup_detail(pid):
        pickup = PickupRequest.query.get_or_404(pid)
        # permission check: household owner, staff assigned, or admin
        if not (current_user.is_admin() or current_user.id==pickup.household_id or (pickup.staff_id and current_user.id==pickup.staff_id)):
            flash("Unauthorized", "danger"); return redirect(url_for('home'))
        items = pickup.items
        return render_template('pickup_detail.html', pickup=pickup, items=items)

    @app.route('/pickup/<int:pid>/cancel', methods=['POST'])
    @login_required
    def cancel_pickup(pid):
        pickup = PickupRequest.query.get_or_404(pid)
        if current_user.id != pickup.household_id:
            flash("Unauthorized", "danger"); return redirect(url_for('home'))
        if pickup.status in ('in_progress','completed'):
            flash("Cannot cancel a pickup in progress or completed", "warning")
        else:
            pickup.status = 'cancelled'
            db.session.commit()
            Notification(recipient_id=pickup.household_id, message=f"Pickup #{pickup.id} cancelled successfully.")
            db.session.add(Notification(recipient_id=pickup.household_id, message=f"Pickup #{pickup.id} cancelled."))
            db.session.commit()
            flash("Pickup cancelled", "success")
        return redirect(url_for('household_dashboard'))

    # Staff dashboard
    @app.route('/staff/dashboard')
    @login_required
    def staff_dashboard():
        if not current_user.is_staff():
            flash("Unauthorized", "danger"); return redirect(url_for('home'))
        assigned = PickupRequest.query.filter_by(staff_id=current_user.id).order_by(PickupRequest.scheduled_date).all()
        return render_template('staff_dashboard.html', assigned=assigned)

    @app.route('/pickup/<int:pid>/update', methods=['GET','POST'])
    @login_required
    def update_pickup_status(pid):
        pickup = PickupRequest.query.get_or_404(pid)
        if not current_user.is_staff() or pickup.staff_id != current_user.id:
            flash("Unauthorized", "danger"); return redirect(url_for('home'))
        form = UpdateStatusForm()
        if form.validate_on_submit():
            pickup.status = form.status.data
            if form.notes.data:
                pickup.notes = (pickup.notes or "") + "\nSTAFF NOTE: " + form.notes.data
            db.session.commit()
            # notify household
            n = Notification(recipient_id=pickup.household_id, message=f"Pickup #{pickup.id} status updated to {pickup.status} by staff {current_user.name or current_user.username}.")
            db.session.add(n); db.session.commit()
            flash("Status updated", "success")
            return redirect(url_for('staff_dashboard'))
        return render_template('pickup_detail.html', pickup=pickup, items=pickup.items, status_form=form)

    # Admin dashboard
    @app.route('/admin/dashboard')
    @login_required
    def admin_dashboard():
        if not current_user.is_admin():
            flash("Unauthorized", "danger"); return redirect(url_for('home'))
        pending = PickupRequest.query.filter_by(status='pending').order_by(PickupRequest.created_at.desc()).all()
        all_requests = PickupRequest.query.order_by(PickupRequest.created_at.desc()).all()
        staff_list = User.query.filter_by(role='staff').all()
        return render_template('admin_dashboard.html', pending=pending, all_requests=all_requests, staff_list=staff_list)

    @app.route('/admin/approve/<int:pid>', methods=['POST'])
    @login_required
    def approve_pickup(pid):
        if not current_user.is_admin():
            flash("Unauthorized", "danger"); return redirect(url_for('home'))
        pickup = PickupRequest.query.get_or_404(pid)
        pickup.status = 'approved'
        db.session.commit()
        Notification(recipient_id=pickup.household_id, message=f"Pickup #{pickup.id} approved by admin.")
        db.session.add(Notification(recipient_id=pickup.household_id, message=f"Your pickup #{pickup.id} has been approved and will be scheduled."))
        db.session.commit()
        flash("Pickup approved", "success")
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/assign/<int:pid>', methods=['POST'])
    @login_required
    def assign_pickup(pid):
        if not current_user.is_admin():
            flash("Unauthorized", "danger"); return redirect(url_for('home'))
        staff_id = int(request.form.get('staff_id'))
        pickup = PickupRequest.query.get_or_404(pid)
        staff = User.query.get(staff_id)
        if staff and staff.is_staff():
            pickup.staff_id = staff_id
            pickup.status = 'scheduled'
            db.session.commit()
            Notification(recipient_id=staff_id, message=f"You have been assigned pickup #{pickup.id}.")
            Notification(recipient_id=pickup.household_id, message=f"Pickup #{pickup.id} assigned to staff {staff.name or staff.username}. Contact: {staff.phone or 'N/A'}")
            db.session.commit()
            flash("Assigned to staff", "success")
        else:
            flash("Invalid staff", "danger")
        return redirect(url_for('admin_dashboard'))

    @app.route('/admin/export')
    @login_required
    def admin_export():
        if not current_user.is_admin():
            flash("Unauthorized", "danger"); return redirect(url_for('home'))
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(['id','household','staff','status','location','scheduled_date','created_at'])
        for r in PickupRequest.query.all():
            cw.writerow([r.id, r.household.username, r.staff.username if r.staff else '', r.status, r.location, r.scheduled_date, r.created_at.isoformat()])
        output = si.getvalue()
        return Response(output, mimetype="text/csv", headers={"Content-disposition":"attachment; filename=pickups.csv"})

    # serve uploaded photos
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # notifications list
    @app.route('/notifications')
    @login_required
    def notifications():
        notes = Notification.query.filter_by(recipient_id=current_user.id).order_by(Notification.created_at.desc()).all()
        return render_template('notifications.html', notifications=notes)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
