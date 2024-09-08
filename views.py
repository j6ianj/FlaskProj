from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, abort 
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from . import db
from .models import User, ProfileForm, PhotoForm, FriendRequest
import os
from datetime import date

views = Blueprint('views', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    form = ProfileForm()
    user = current_user
    today = date.today()
    user_age = today.year - user.birthdate.year - ((today.month, today.day) < (user.birthdate.month, user.birthdate.day))
    user.age = user_age
    return render_template("home.html", user=current_user, form=form)

@views.route('/set-location', methods=['GET', 'POST'])
@login_required
def set_location():
    if request.method == 'POST':
        location = request.form.get('location')
        if location:
            current_user.location = location
            db.session.commit()
            flash('Location set successfully!', category='success')
            return redirect(url_for('views.create_bio'))
        else:
            flash('Please enter a location.', category='error')
    google_places_api_key = current_app.config['GOOGLE_PLACES_API_KEY']
    return render_template("set_location.html", user=current_user, google_places_api_key=google_places_api_key)

@views.route('/create-bio', methods=['GET', 'POST'])
@login_required
def create_bio():
    if request.method == 'POST':
        bio = request.form.get('bio')
        if bio:
            current_user.bio = bio
            db.session.commit()
            flash('Bio updated successfully!', category='success')
            return redirect(url_for('views.add_pics'))
        else:
            flash('Please enter a bio.', category='error')
    return render_template("bio.html", user=current_user)

@views.route('/add-pics', methods=['GET', 'POST'])
@login_required
def add_pics():
    form = PhotoForm()
    if form.validate_on_submit():
        if 'profilePhoto' in request.files:
            files = request.files.getlist('profilePhoto')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    if current_user.photos:
                        current_user.photos.append(filename)
                    else:
                        current_user.photos = [filename]
            db.session.commit()
            flash('Photos uploaded successfully!', category='success')
        else:
            flash('Invalid file type.', category='error')
    return render_template("pics.html", form=form, user=current_user, photos=current_user.photos)

@views.route('/update-profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    form = ProfileForm()
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.bio = form.bio.data

        if 'profilePhoto' in request.files:
            file = request.files['profilePhoto']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                if current_user.photos:
                    current_user.photos.append(filename)
                else:
                    current_user.photos = [filename]
                db.session.commit()
                flash('Profile updated successfully!', category='success')
                return redirect(url_for('views.home'))
            else:
                flash('Invalid file type.', category='error')
        db.session.commit()
        flash('Profile updated successfully!', category='success')
        return redirect(url_for('views.home'))
    elif request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.bio.data = current_user.bio

    return render_template("home.html", form=form, user=current_user)

@views.route('/add_friend/<int:friend_id>', methods=['POST'])
@login_required
def add_friend(friend_id):
    friend = User.query.get(friend_id)
    if friend and current_user.add_friend(friend):
        db.session.commit()
        flash(f'You are now friends with {friend.first_name}!', 'success')
    else:
        flash('Failed to add friend or friend limit reached.', 'danger')
    return redirect(url_for('views.home', user_id=friend_id))

@views.route('/remove_friend/<int:friend_id>', methods=['POST'])
@login_required
def remove_friend(friend_id):
    friend = User.query.get(friend_id)
    if friend and current_user.remove_friend(friend):
        db.session.commit()
        flash(f'You are no longer friends with {friend.first_name}.', 'success')
    else:
        flash('Failed to remove friend.', 'danger')
    return redirect(url_for('views.profile', user_id=friend_id))

@views.route('/friends')
@login_required
def friends():
    return render_template('friends.html', friends=current_user.friends)

@views.route('/profile/<int:user_id>')
def profile(user_id):
    user = User.query.get(user_id)
    if not user:
        abort(404)
    return render_template('profile.html', user=user)

@views.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    query = request.args.get('query')
    if query:
        results = User.query.filter(User.phoneNum.like(f'%{query}%')).all()
    else:
        results = []
    return render_template('search_results.html', results=results)

@views.route('/send_request', methods=['POST'])
@login_required
def send_request():
    phone_number = request.form.get('phone_number')
    if phone_number:
        user = User.query.filter_by(phoneNum=phone_number).first()
        if user and current_user.send_request(user):
            db.session.commit()
            flash(f'Friend request sent to {user.first_name}!', 'success')
        else:
            flash('Failed to send friend request. User may not exist or you have already sent a request.', 'danger')
    else:
        flash('Please enter a valid phone number.', 'danger')
    return redirect(url_for('views.pending_requests'))

@views.route('/accept_friend_request/<int:user_id>', methods=['POST'])
@login_required
def accept_friend_request(user_id):
    friend_request = FriendRequest.query.filter_by(sender_id=user_id, receiver_id=current_user.id, status='pending').first()
    if friend_request:
        friend_request.status = 'accepted'
        db.session.commit()
        flash('Friend request accepted!', 'success')
    else:
        flash('Failed to accept friend request.', 'danger')
    return redirect(url_for('views.pending_requests'))

@views.route('/reject_friend_request/<int:user_id>', methods=['POST'])
@login_required
def reject_friend_request(user_id):
    friend_request = FriendRequest.query.filter_by(sender_id=user_id, receiver_id=current_user.id, status='pending').first()
    if friend_request:
        friend_request.status = 'rejected'
        db.session.commit()
        flash('Friend request rejected.', 'success')
    else:
        flash('Failed to reject friend request.', 'danger')
    return redirect(url_for('views.pending_requests'))

@views.route('/friend_requests')
@login_required
def friend_requests():
    return render_template('friend_requests.html', received_requests=current_user.received_requests.all())

@views.route('/pending_requests')
@login_required
def pending_requests():
    sent_requests = FriendRequest.query.filter_by(sender_id=current_user.id, status='pending').all()
    received_requests = FriendRequest.query.filter_by(receiver_id=current_user.id, status='pending').all()
    return render_template('pending_requests.html', sent_requests=sent_requests, received_requests=received_requests)

@views.route('/match', methods=['GET', 'POST'])
@login_required
def match():
    user = current_user
    if user.gender is None or user.preference is None:
        flash('Please complete your gender and preference settings in your profile.', 'warning')
        return redirect(url_for('views.update_profile'))

    min_age = user.age() - 5
    max_age = user.age() + 5

    potential_matches = User.query.filter(
        User.gender == user.preference,
        User.preference == user.gender,
        User.id != user.id,
        User.birthdate.between(
            date(date.today().year - max_age, 1, 1),
            date(date.today().year - min_age, 12, 31)
        )
    ).all()

    return render_template('match.html', matches=potential_matches)
@views.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user = current_user
    form = ProfileForm(obj=user)

    if form.validate_on_submit():
        form.populate_obj(user)  # Update the user object with form data

        # Handle profile photo upload
        if form.profilePhoto.data:
            photo_file = save_profile_photo(form.profilePhoto.data)
            user.profile_photo = photo_file

        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('views.settings'))

    return render_template('settings.html', form=form, user=user)

def save_profile_photo(photo_data):
    # Function to save uploaded profile photo
    filename = secure_filename(photo_data.filename)
    filepath = os.path.join(current_app.root_path, 'static/uploads', filename)
    photo_data.save(filepath)
    return filename

