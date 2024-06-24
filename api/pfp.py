from flask import Blueprint, g, request, current_app as app
from flask_restful import Api, Resource
import base64
from api.auth_middleware import token_required
from model.users import User
from __init__ import db
import os
from werkzeug.utils import secure_filename

pfp_api = Blueprint('pfp_api', __name__, url_prefix='/api/id')
api = Api(pfp_api)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in [ext.strip('.') for ext in app.config['UPLOAD_EXTENSIONS']]

class _PFP(Resource):
    def post(self):
        if 'file' not in request.files:
            return {'message': 'Please upload an image first'}, 400

        file = request.files['file']
        if file.filename == '':
            return {'message': 'No selected file'}, 400

        if not allowed_file(file.filename):
            return {'message': 'File type not allowed'}, 400
        
        if file.content_length > app.config['MAX_CONTENT_LENGTH']:
            return {'message': 'File size exceeds the allowed limit'}, 400
        
        user_uid = request.form.get('uid')
        if not user_uid:
            return {'message': 'UID required.'}, 400

        user = User.query.filter_by(_uid=user_uid).first()
        if not user:
            return {'message': 'User not found'}, 404

        try:
            filename = secure_filename(file.filename)
            user_dir = os.path.join(app.config['UPLOAD_FOLDER'], user_uid)
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)
            file_path = os.path.join(user_dir, filename)
            file.save(file_path)
            user._pfp = os.path.join(filename)
            db.session.commit()
            return {'message': 'Profile picture updated successfully'}, 200
        except Exception as e:
            db.session.rollback()
            return {'message': f'An error occurred while updating the profile picture: {str(e)}'}, 500

    @token_required()
    def get(self):
        # retrieve the current user from the token_required authentication check  
        current_user = g.current_user

        if current_user._pfp:
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.uid, current_user.pfp)
            try:
                with open(img_path, 'rb') as img_file:
                    base64_encoded = base64.b64encode(img_file.read()).decode('utf-8')
                    return {'pfp': base64_encoded}, 200
            except FileNotFoundError:
                return {'message': 'Profile picture file not found.'}, 404
        else:
            return {'message': 'Profile picture not set.'}, 404
    
    @token_required()
    def delete(self):
        
        current_user = g.current_user

        if current_user.role != 'Admin':
            return {'message': 'Unauthorized.'}, 401

        user_uid = request.args.get('uid')
        if not user_uid:
            return {'message': 'UID required.'}, 400

        user = User.query.filter_by(_uid=user_uid).first()
        if not user:
            return {'message': 'User not found'}, 404

        if user._pfp:
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], user_uid, user._pfp)
            try:
                if os.path.exists(img_path):
                    os.remove(img_path)
                user._pfp = None
                db.session.commit()
                return {'message': 'Profile picture deleted successfully'}, 200
            except Exception as e:
                db.session.rollback()
                return {'message': f'An error occurred while deleting the profile picture: {str(e)}'}, 500
        else:
            return {'message': 'Profile picture not set.'}, 404
    
api.add_resource(_PFP, '/pfp')
