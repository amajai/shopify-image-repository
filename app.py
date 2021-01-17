import datetime
from flask import Flask, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, BooleanField, RadioField, MultipleFileField
from wtforms.validators import InputRequired, Length
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

from flask_bootstrap import Bootstrap
import boto3
from config import S3_BUCKET, S3_Key, S3_SECRET, S3_LOCATION, SECRET_KEY


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = SECRET_KEY

db = SQLAlchemy(app)
Bootstrap(app)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(15), unique=True)
    images = db.relationship('Image', backref='owner')
    password = db.Column(db.String(80))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.Text, unique=True, nullable=False)
    image_name = db.Column(db.Text, nullable=False)
    permission = db.Column(db.Text, nullable=False)
    date_posted =  db.Column(db.DateTime, default=datetime.datetime.utcnow)
    owner_name = db.Column(db.Text, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class LoginForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(),])
    password = PasswordField('password', validators=[InputRequired(),])
    remember = BooleanField('remember me')

class RegisterForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(),])
    password = PasswordField('password', validators=[InputRequired(),])

class UploadForm(FlaskForm):
    upload = MultipleFileField('Add images')
    image_name = StringField('Image name', validators=[InputRequired(),])
    permission = RadioField ('permission',default='public',choices=[('public', 'Public'),('private', 'Private')])


s3 = boto3.client(
    's3',
    aws_access_key_id=S3_Key,
    aws_secret_access_key=S3_SECRET
)

def unique_filename(filename):
    suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    new_filename = "_".join([filename, suffix]) # e.g. 'mylogfile_120508_171442
    return new_filename

def upload_file_to_s3(file, bucket_name, acl="public-read"):
    new_filename = unique_filename(file.filename)
    try:
        s3.upload_fileobj(
            file,
            bucket_name,
            new_filename,
            ExtraArgs={
                "ACL": acl,
                "ContentType": file.content_type
            }
        )

    except Exception as e:
        # This is a catch all exception, edit this part to fit your needs.
        print("Something Happened: ", e)
        return e
    
    return "{}{}".format(S3_LOCATION, new_filename)



@app.route('/', methods=['GET','POST'])
def home():
    images = Image.query.order_by(Image.date_posted.desc()).filter_by(permission='public').all()
    return render_template('index.html', images=images)

@app.route('/upload', methods=['GET','POST'])
@login_required
def upload():
    form = UploadForm()
    if form.validate_on_submit():
        pics = form.upload.data
        for pic in pics:
            if not pic:
                return 'No pic uploaded!', 400
            output= upload_file_to_s3(pic, S3_BUCKET)
            filename=form.image_name.data
            img = Image(image_url=output, 
                        image_name=filename, 
                        permission=form.permission.data, 
                        owner_id=current_user.id,
                        owner_name=current_user.username
                        )
            db.session.add(img)
            db.session.commit()
        flash('You have successfully uploaded an image!', 'success')
        return redirect(url_for('home'))
        
    return render_template('upload.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if user.password == form.password.data:
                login_user(user, remember=form.remember.data)
                flash('Welcome, '+ str(user.username) + '!', 'success')
                return redirect(url_for('profile'))
        flash('Invalid username or password', 'danger')

    return render_template('login.html', form=form)

@app.route('/profile')
@login_required
def profile():
    images = Image.query.order_by(Image.date_posted.desc()).filter(Image.owner_id==current_user.id).all()
    return render_template('profile.html', images=images)    

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            new_user = User(username=form.username.data, password=form.password.data)
            db.session.add(new_user)
            db.session.commit()
        except Exception as e:
            return  'Error: '+ str(e)
        flash('New User has been created!', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have successfully logged out!', 'success')
    return redirect(url_for('home'))

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    image_to_delete=Image.query.get_or_404(id)
    try:
        db.session.delete(image_to_delete)
        db.session.commit()
        flash('Image successfully deleted!', 'info')
    except:
        return 'There was a problem deleting the image.'
    return redirect(url_for('home'))
