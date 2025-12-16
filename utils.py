import os
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

def hash_password(password):
    return generate_password_hash(password)

def verify_password(hash_pw, password):
    return check_password_hash(hash_pw, password)

def allowed_file(filename):
    allowed_ext = {'png','jpg','jpeg','gif'}
    return '.' in filename and filename.rsplit('.',1)[1].lower() in allowed_ext

def ensure_upload_folder():
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
