from . import db
from flask_wtf import FlaskForm
from flask_login import UserMixin
from wtforms import SelectField, StringField, PasswordField, SubmitField, BooleanField, TextAreaField, DateField, FileField, MultipleFileField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Regexp
from datetime import date

# Association table for friendships
friendship = db.Table('friendship',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

# Association table for friend requests
friend_requests = db.Table('friend_requests',
    db.Column('requester_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('receiver_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    first_name = db.Column(db.String(150), nullable=False)
    phoneNum = db.Column(db.String(15), unique=True, nullable=False)
    birthdate = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(150), nullable=True)
    gender = db.Column(db.String(150), nullable=True)
    preference = db.Column(db.String(150), nullable=True)  # Preference
    height = db.Column(db.Integer, nullable=True)
    hometown = db.Column(db.String(150), nullable=True)
    college = db.Column(db.String(150), nullable=True)
    bio = db.Column(db.String(150), nullable=True)
    photos = db.Column(db.PickleType, nullable=True)
    
    sent_requests = db.relationship('User', secondary=friend_requests, primaryjoin=id==friend_requests.c.requester_id,
    secondaryjoin=id==friend_requests.c.receiver_id, backref=db.backref('received_requests', lazy='dynamic'))

    friends = db.relationship('User', secondary=friendship, primaryjoin=id==friendship.c.user_id,
    secondaryjoin=id==friendship.c.friend_id, backref=db.backref('friend_of', lazy='dynamic'))

    def send_request(self, user):
        if not self.has_sent_request(user) and not self.is_friend(user):
            friend_request = FriendRequest(sender_id=self.id, receiver_id=user.id, status='pending')
            db.session.add(friend_request)
            return True
        return False


    def remove_request(self, user):
        if self.has_sent_request(user):
            self.sent_requests.remove(user)
            return True
        return False

    def has_sent_request(self, user):
        return user in self.sent_requests

    def has_received_request(self,user):
        return user in self.received_requests 

    def accept_request(self, user):
        friend_request = FriendRequest.query.filter_by(sender_id=user.id, receiver_id=self.id, status='pending').first()
        if friend_request:
            self.add_friend(user)
            user.add_friend(self)
            friend_request.status = 'accepted'
            return True
        return False


    def reject_request(self, user):
        if user in self.received_requests:
            self.received_requests.remove(user)
            return True
        return False

    def add_friend(self, friend):
        if not self.is_friend(friend) and self.friend_count() < 10:
            self.friends.append(friend)
            return True
        return False

    def remove_friend(self, friend):
        if self.is_friend(friend):
            self.friends.remove(friend)
            return True
        return False

    def is_friend(self, user):
        return user in self.friends

    def friend_count(self):
        return len(self.friends)
    
    def age(self):
        today = date.today()
        return today.year - self.birthdate.year - ((today.month, today.day) < (self.birthdate.month, self.birthdate.day))

class FriendRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_friend_requests')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_friend_requests')

class PhotoForm(FlaskForm):
    profilePhoto = MultipleFileField('Upload Profile Photo', validators=[DataRequired()], render_kw={"multiple": True})
    submit = SubmitField('Upload')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    phoneNum = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15), Regexp(r'^\+?1?\d{9,15}$', message="Invalid phone number")])
    birthdate = DateField('Birthdate', validators=[DataRequired()], format='%Y-%m-%d')
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')

    def validate_phoneNum(self, phoneNum):
        user = User.query.filter_by(phoneNum=phoneNum.data).first()
        if user:
            raise ValidationError('That phone number is already in use. Please use a different one.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class ProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    bio = TextAreaField('Bio', validators=[DataRequired()])
    gender = SelectField('Your Gender', choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], validators=[DataRequired()])
    preference = SelectField('Preferred Gender', choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    height = StringField('Height')
    college = StringField('College')
    hometown = StringField('Hometown')
    profilePhoto = FileField('Profile Picture')  # Support for photo uploads
    submit = SubmitField('Update Profile')
