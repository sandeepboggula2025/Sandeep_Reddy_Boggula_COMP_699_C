from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, IntegerField, SelectField, DateField, FileField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange

class LoginForm(FlaskForm):
    username = StringField("Username or Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class HouseholdRegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo('password')])
    name = StringField("Full name", validators=[Optional()])
    address = StringField("Address", validators=[Optional()])
    phone = StringField("Phone", validators=[Optional()])
    submit = SubmitField("Register")

class StaffRegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo('password')])
    name = StringField("Full name", validators=[Optional()])
    submit = SubmitField("Register as Staff")

class PickupRequestForm(FlaskForm):
    location = StringField("Pickup Address", validators=[DataRequired()])
    scheduled_date = StringField("Preferred Date (YYYY-MM-DD)", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])
    photo = FileField("Photo (optional)")
    submit = SubmitField("Submit Pickup Request")

class ItemDetailForm(FlaskForm):
    item_type = StringField("Item Type (e.g., Laptop)", validators=[DataRequired()])
    quantity = IntegerField("Quantity", default=1, validators=[DataRequired(), NumberRange(min=1)])
    condition_status = StringField("Condition (e.g., Working/Not Working)", validators=[Optional()])
    submit = SubmitField("Add Item")

class UpdateStatusForm(FlaskForm):
    status = SelectField("Status", choices=[('scheduled','Scheduled'),('in_progress','In Progress'),('completed','Completed'),('failed','Failed'),('cancelled','Cancelled')], validators=[DataRequired()])
    notes = TextAreaField("Staff notes", validators=[Optional()])
    submit = SubmitField("Update Status")
