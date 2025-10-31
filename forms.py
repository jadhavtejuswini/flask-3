from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired, Email, NumberRange

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

class StudentForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    roll_no = StringField("Roll Number", validators=[DataRequired()])
    student_class = StringField("Class", validators=[DataRequired()])
    submit = SubmitField("Save")

class SubjectForm(FlaskForm):
    name = StringField("Subject Name", validators=[DataRequired()])
    submit = SubmitField("Save")

class MarksForm(FlaskForm):
    student = SelectField("Student", coerce=int, validators=[DataRequired()])
    subject = SelectField("Subject", coerce=int, validators=[DataRequired()])
    marks = IntegerField("Marks", validators=[DataRequired(), NumberRange(min=0, max=100)])
    submit = SubmitField("Save")
