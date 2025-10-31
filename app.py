from flask import Flask, render_template, redirect, url_for, flash, request, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, User, Student, Subject, Result
from forms import LoginForm, StudentForm, SubjectForm, MarksForm
import io
from reportlab.pdfgen import canvas
from functools import wraps
import logging

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    # Enable SQLAlchemy error logging (helps debug the INSERT issue)
    logging.basicConfig()

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- Create tables & default admin ---
    with app.app_context():
        db.create_all()

        admin = User.query.filter_by(username="admin").first()
        if not admin:
            try:
                admin = User(username="admin", role="admin")
                admin.set_password("admin123")
                db.session.add(admin)
                db.session.commit()
                print("✅ Default admin created successfully!")
            except Exception as e:
                db.session.rollback()
                print("⚠️ Error creating default admin:", e)

    # --- Decorator for admin-only routes ---
    def admin_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != "admin":
                flash("You do not have access to that page.")
                return redirect(url_for("login"))
            return fn(*args, **kwargs)
        return wrapper

    # --- Routes ---

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            if current_user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("student_dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                if user.role == "admin":
                    return redirect(url_for("admin_dashboard"))
                else:
                    return redirect(url_for("student_dashboard"))
            flash("Invalid username or password")
        return render_template("login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    # --- Admin Routes ---
    @app.route("/admin/dashboard")
    @login_required
    @admin_required
    def admin_dashboard():
        student_count = Student.query.count()
        subject_count = Subject.query.count()
        results_count = Result.query.count()
        return render_template("admin_dashboard.html",
                               student_count=student_count,
                               subject_count=subject_count,
                               results_count=results_count)

    @app.route("/admin/students")
    @login_required
    @admin_required
    def list_students():
        students = Student.query.all()
        return render_template("list_students.html", students=students)

    @app.route("/admin/student/add", methods=["GET", "POST"])
    @login_required
    @admin_required
    def add_student():
        form = StudentForm()
        if form.validate_on_submit():
            # Check for existing student
            if User.query.filter_by(username=form.roll_no.data).first() or Student.query.filter_by(roll_no=form.roll_no.data).first():
                flash("User with this roll number already exists.")
                return redirect(url_for("add_student"))

            student = Student(
                name=form.name.data,
                email=form.email.data,
                roll_no=form.roll_no.data,
                student_class=form.student_class.data
            )
            db.session.add(student)

            # Create login for student
            user = User(username=form.roll_no.data, role="student")
            user.set_password(form.roll_no.data)
            db.session.add(user)

            try:
                db.session.commit()
                flash("Student added successfully")
            except Exception as e:
                db.session.rollback()
                flash(f"Error adding student: {e}")
            return redirect(url_for("list_students"))
        return render_template("add_student.html", form=form)

    @app.route("/admin/student/edit/<int:student_id>", methods=["GET", "POST"])
    @login_required
    @admin_required
    def edit_student(student_id):
        student = Student.query.get_or_404(student_id)
        form = StudentForm(obj=student)
        if form.validate_on_submit():
            if student.roll_no != form.roll_no.data and (User.query.filter_by(username=form.roll_no.data).first() or Student.query.filter_by(roll_no=form.roll_no.data).first()):
                flash("Roll number already in use.")
                return redirect(url_for("edit_student", student_id=student_id))

            old_roll = student.roll_no
            student.name = form.name.data
            student.email = form.email.data
            student.roll_no = form.roll_no.data
            student.student_class = form.student_class.data

            user = User.query.filter_by(username=old_roll).first()
            if user:
                user.username = student.roll_no

            try:
                db.session.commit()
                flash("Student updated")
            except Exception as e:
                db.session.rollback()
                flash(f"Error updating student: {e}")

            return redirect(url_for("list_students"))
        return render_template("add_student.html", form=form)

    @app.route("/admin/student/delete/<int:student_id>")
    @login_required
    @admin_required
    def delete_student(student_id):
        student = Student.query.get_or_404(student_id)
        user = User.query.filter_by(username=student.roll_no).first()
        if user:
            db.session.delete(user)
        db.session.delete(student)
        db.session.commit()
        flash("Student deleted")
        return redirect(url_for("list_students"))

    @app.route("/admin/subjects")
    @login_required
    @admin_required
    def list_subjects():
        subjects = Subject.query.all()
        return render_template("list_subjects.html", subjects=subjects)

    @app.route("/admin/subject/add", methods=["GET", "POST"])
    @login_required
    @admin_required
    def add_subject():
        form = SubjectForm()
        if form.validate_on_submit():
            existing = Subject.query.filter_by(name=form.name.data).first()
            if existing:
                flash("Subject already exists.")
                return redirect(url_for("add_subject"))
            subj = Subject(name=form.name.data)
            db.session.add(subj)
            db.session.commit()
            flash("Subject added")
            return redirect(url_for("list_subjects"))
        return render_template("add_subject.html", form=form)

    @app.route("/admin/subject/delete/<int:subject_id>")
    @login_required
    @admin_required
    def delete_subject(subject_id):
        subj = Subject.query.get_or_404(subject_id)
        db.session.delete(subj)
        db.session.commit()
        flash("Subject deleted")
        return redirect(url_for("list_subjects"))

    @app.route("/admin/marks", methods=["GET", "POST"])
    @login_required
    @admin_required
    def add_marks():
        form = MarksForm()
        form.student.choices = [(s.id, f"{s.name} ({s.roll_no})") for s in Student.query.order_by(Student.name).all()]
        form.subject.choices = [(s.id, s.name) for s in Subject.query.order_by(Subject.name).all()]
        if form.validate_on_submit():
            result = Result.query.filter_by(student_id=form.student.data, subject_id=form.subject.data).first()
            if result:
                result.marks = form.marks.data
            else:
                result = Result(student_id=form.student.data, subject_id=form.subject.data, marks=form.marks.data)
                db.session.add(result)
            db.session.commit()
            flash("Marks saved/updated")
            return redirect(url_for("add_marks"))
        return render_template("add_marks.html", form=form)

    # --- Student Routes ---
    @app.route("/student/dashboard")
    @login_required
    def student_dashboard():
        if current_user.role != "student":
            flash("Access denied")
            return redirect(url_for("login"))
        student = Student.query.filter_by(roll_no=current_user.username).first()
        if not student:
            flash("Student profile not found")
            return redirect(url_for("logout"))
        return render_template("student_dashboard.html", student=student)

    @app.route("/student/results")
    @login_required
    def view_results():
        if current_user.role != "student":
            flash("Access denied")
            return redirect(url_for("login"))
        student = Student.query.filter_by(roll_no=current_user.username).first()
        results = student.results if student else []
        return render_template("view_results.html", student=student, results=results)

    @app.route("/student/report")
    @login_required
    def report_card():
        if current_user.role != "student":
            flash("Access denied")
            return redirect(url_for("login"))
        student = Student.query.filter_by(roll_no=current_user.username).first()
        results = student.results if student else []

        buffer = io.BytesIO()
        p = canvas.Canvas(buffer)
        y = 800
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, y, f"Report Card for {student.name} ({student.roll_no})")
        y -= 30
        p.setFont("Helvetica", 12)
        if not results:
            p.drawString(100, y, "No results available.")
        else:
            for r in results:
                subjname = r.subject.name if r.subject else "Unknown Subject"
                p.drawString(100, y, f"{subjname}: {r.marks}")
                y -= 20
                if y < 60:
                    p.showPage()
                    y = 800
        p.showPage()
        p.save()
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="report.pdf", mimetype="application/pdf")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)