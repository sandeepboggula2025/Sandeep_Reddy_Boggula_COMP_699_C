from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='household')  # 'household', 'staff', 'admin'
    name = db.Column(db.String(120))
    address = db.Column(db.String(255))
    phone = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_household(self):
        return self.role == 'household'
    def is_staff(self):
        return self.role == 'staff'
    def is_admin(self):
        return self.role == 'admin'

class PickupRequest(db.Model):
    __tablename__ = 'pickup_requests'
    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(30), default='pending')  # pending, approved, scheduled, in_progress, completed, cancelled, failed, rejected
    location = db.Column(db.String(255))
    scheduled_date = db.Column(db.String(30))  # store as yyyy-mm-dd string for simplicity
    notes = db.Column(db.Text, nullable=True)
    photo_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    household = db.relationship('User', foreign_keys=[household_id], backref='requests_made')
    staff = db.relationship('User', foreign_keys=[staff_id], backref='requests_assigned')

class ItemDetail(db.Model):
    __tablename__ = 'item_details'
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('pickup_requests.id'), nullable=False)
    item_type = db.Column(db.String(120))
    quantity = db.Column(db.Integer, default=1)
    condition_status = db.Column(db.String(120), nullable=True)

    pickup_request = db.relationship('PickupRequest', backref='items')

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    recipient = db.relationship('User', backref='notifications')
