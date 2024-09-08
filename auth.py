from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db   # from __init__.py import db
from flask_login import login_user, login_required, logout_user, current_user
from datetime import date, datetime

auth = Blueprint('auth', __name__)

def calculate_age(birthdate):
    today = date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_or_phone = request.form.get('email_or_phone')
        password = request.form.get('password')

        user = User.query.filter((User.email==email_or_phone) | (User.phoneNum==email_or_phone)).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect password, try again.', category='error')
        else:
            flash('Email or phone number does not exist.', category='error')

    return render_template("login.html", user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        phoneNum = request.form.get('phoneNum')
        birthdate_str = request.form.get('birthdate')
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        try:
            birthdate = datetime.strptime(birthdate_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid birthdate format. Please use YYYY-MM-DD.', category='error')
            return render_template("sign-up.html", user=current_user)

        user_by_email = User.query.filter_by(email=email).first()
        user_by_phone = User.query.filter_by(phoneNum=phoneNum).first()
        if user_by_email:
            flash('Email already exists.', category='error')
        elif user_by_phone:
            flash('Phone number already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif len(first_name) < 2:
            flash('First name must be greater than 1 character.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
        elif calculate_age(birthdate) < 18:
            flash('You must be at least 18 years old to sign up.', category='error')
        else:
            new_user = User(email=email, first_name=first_name, birthdate=birthdate, phoneNum=phoneNum, password=generate_password_hash(password1, method='pbkdf2:sha256'))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('Account created!', category='success')
            return redirect(url_for('views.set_location'))

    return render_template("sign-up.html", user=current_user)
