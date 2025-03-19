"""
Application routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from .models import User, Template, Message
from .services import GammuService
import re

# Initialize blueprints
auth_bp = Blueprint('auth', __name__)
admin_bp = Blueprint('admin', __name__)
user_bp = Blueprint('user', __name__)

# Initialize Gammu service
gammu_service = GammuService()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Authentication routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.get_by_username(username)
        if user and user['password'] == password:  # In production, use proper password hashing
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            
            if user['is_admin']:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('user.send_sms'))
        
        flash('Invalid username or password')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

# Admin routes
@admin_bp.route('/admin')
@admin_required
def dashboard():
    return render_template('admin_dashboard.html')

@admin_bp.route('/admin/users', methods=['GET', 'POST'])
@admin_required
def manage_users():
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username')
        password = request.form.get('password')
        
        if action == 'add':
            if User.create(username, password):
                flash('User added successfully')
            else:
                flash('Username already exists')
        elif action == 'delete':
            if User.delete(username):
                flash('User deleted successfully')
            else:
                flash('Failed to delete user')
    
    return render_template('manage_users.html')

@admin_bp.route('/admin/templates', methods=['GET', 'POST'])
@admin_required
def manage_templates():
    if request.method == 'POST':
        action = request.form.get('action')
        title = request.form.get('title')
        content = request.form.get('content')
        
        if action == 'add':
            if Template.create(title, content):
                flash('Template added successfully')
            else:
                flash('Template title already exists')
        elif action == 'update':
            if Template.update(title, content):
                flash('Template updated successfully')
            else:
                flash('Failed to update template')
        elif action == 'delete':
            if Template.delete(title):
                flash('Template deleted successfully')
            else:
                flash('Failed to delete template')
    
    templates = Template.get_all()
    return render_template('manage_templates.html', templates=templates)

@admin_bp.route('/admin/report')
@admin_required
def sms_report():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    phone = request.args.get('phone')
    
    offset = (page - 1) * per_page
    
    if phone:
        messages = Message.get_by_phone(phone, per_page, offset)
    else:
        messages = Message.get_all(per_page, offset)
    
    return render_template('sms_report.html', messages=messages, page=page, per_page=per_page)

@admin_bp.route('/admin/report/delete/<int:message_id>', methods=['POST'])
@admin_required
def delete_message(message_id):
    if Message.delete(message_id):
        flash('Message deleted successfully')
    else:
        flash('Failed to delete message')
    return redirect(url_for('admin.sms_report'))

@admin_bp.route('/admin/report/delete-all', methods=['POST'])
@admin_required
def delete_all_messages():
    if Message.delete_all():
        flash('All messages deleted successfully')
    else:
        flash('Failed to delete messages')
    return redirect(url_for('admin.sms_report'))

# User routes
@user_bp.route('/send-sms', methods=['GET', 'POST'])
@login_required
def send_sms():
    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        message = request.form.get('message')
        
        # Validate phone number
        if not re.match(r'^07\d{9}$', phone_number):
            flash('Invalid phone number. Must start with 07 and be 11 digits long.')
            return render_template('send_sms.html')
        
        # Check for repeated characters
        if re.search(r'(.)\1{3,}', message):
            flash('Message contains too many repeated characters.')
            return render_template('send_sms.html')
        
        # Create message record
        message_id = Message.create(phone_number, message, session['user_id'])
        if message_id:
            # Send message
            if gammu_service.send_sms(phone_number, message, message_id):
                flash('Message sent successfully')
            else:
                flash('Failed to send message')
        else:
            flash('Failed to save message')
        
        return redirect(url_for('user.send_sms'))
    
    templates = Template.get_all()
    return render_template('send_sms.html', templates=templates)

@user_bp.route('/get-template/<title>')
@login_required
def get_template(title):
    template = Template.get_by_title(title)
    if template:
        return jsonify({'content': template['content']})
    return jsonify({'error': 'Template not found'}), 404 