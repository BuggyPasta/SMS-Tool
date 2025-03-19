"""
Application routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from .models import User, Template, Message
from .services import GammuService, GammuError, ModemError, SIMError, NetworkError
import re
import logging

# Initialize blueprints
auth_bp = Blueprint('auth', __name__)
admin_bp = Blueprint('admin', __name__)
user_bp = Blueprint('user', __name__)

# Initialize Gammu service
gammu_service = GammuService()

logger = logging.getLogger(__name__)

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
        
        user = User.authenticate(username, password)
        if user:
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            if user.is_admin and user.password == 'admin':
                flash('Please change your default admin password!', 'warning')
            return redirect(url_for('admin.dashboard' if user.is_admin else 'user.dashboard'))
        flash('Invalid username or password', 'error')
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
                flash('User added successfully', 'success')
            else:
                flash('Username already exists', 'error')
        elif action == 'delete':
            if User.delete(username):
                flash('User deleted successfully', 'success')
            else:
                flash('Failed to delete user', 'error')
    
    users = User.get_all()
    return render_template('manage_users.html', users=users)

@admin_bp.route('/admin/templates', methods=['GET', 'POST'])
@admin_required
def manage_templates():
    if request.method == 'POST':
        action = request.form.get('action')
        title = request.form.get('title')
        content = request.form.get('content')
        
        if action == 'add':
            if Template.create(title, content):
                flash('Template added successfully', 'success')
            else:
                flash('Template title already exists', 'error')
        elif action == 'update':
            if Template.update(title, content):
                flash('Template updated successfully', 'success')
            else:
                flash('Failed to update template', 'error')
        elif action == 'delete':
            if Template.delete(title):
                flash('Template deleted successfully', 'success')
            else:
                flash('Failed to delete template', 'error')
    
    templates = Template.get_all()
    return render_template('manage_templates.html', templates=templates)

@admin_bp.route('/admin/report')
@admin_required
def sms_report():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    phone_number = request.args.get('phone_number')
    
    messages = Message.get_all(page, per_page, phone_number)
    total_pages = Message.get_total_pages(per_page, phone_number)
    
    return render_template('sms_report.html', messages=messages, total_pages=total_pages, current_page=page, per_page=per_page)

@admin_bp.route('/admin/report/delete/<int:message_id>', methods=['POST'])
@admin_required
def delete_message(message_id):
    if Message.delete(message_id):
        flash('Message deleted successfully', 'success')
    else:
        flash('Failed to delete message', 'error')
    return redirect(url_for('admin.sms_report'))

@admin_bp.route('/admin/report/delete-all', methods=['POST'])
@admin_required
def delete_all_messages():
    if Message.delete_all():
        flash('All messages deleted successfully', 'success')
    else:
        flash('Failed to delete messages', 'error')
    return redirect(url_for('admin.sms_report'))

@admin_bp.route('/admin/health')
@admin_required
def health_check():
    try:
        # Check database connection
        User.get_all()
        # Check Gammu connection
        gammu_service.connect()
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# User routes
@user_bp.route('/')
@login_required
def dashboard():
    templates = Template.get_all()
    return render_template('user_dashboard.html', templates=templates)

@user_bp.route('/send-sms', methods=['GET', 'POST'])
@login_required
def send_sms():
    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        message = request.form.get('message')
        
        # Validate phone number
        if not re.match(r'^07\d{9}$', phone_number):
            flash('Invalid phone number. Must start with 07 and be 11 digits long.', 'error')
            return render_template('send_sms.html')
        
        # Check for repeated characters
        if re.search(r'(.)\1{3,}', message):
            flash('Message contains too many repeated characters. Please correct and try again.', 'error')
            return render_template('send_sms.html')
        
        try:
            # Create message record
            message_id = Message.create(phone_number, message, session['user_id'])
            if message_id:
                # Send message
                if gammu_service.send_sms(phone_number, message, message_id):
                    Message.update_status(message_id, 'sent')
                    flash('Message sent successfully', 'success')
                else:
                    Message.update_status(message_id, 'failed')
                    flash('Failed to send message. Please try again.', 'error')
            else:
                flash('Failed to save message. Please try again.', 'error')
        except ModemError as e:
            logger.error(f"Modem error: {str(e)}")
            Message.update_status(message_id, 'failed')
            flash(f'Modem error: {str(e)}. Please check the modem connection.', 'error')
        except SIMError as e:
            logger.error(f"SIM error: {str(e)}")
            Message.update_status(message_id, 'failed')
            flash(f'SIM card error: {str(e)}. Please check the SIM card.', 'error')
        except NetworkError as e:
            logger.error(f"Network error: {str(e)}")
            Message.update_status(message_id, 'failed')
            flash(f'Network error: {str(e)}. Please check the network connection.', 'error')
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            Message.update_status(message_id, 'failed')
            flash(f'Message validation error: {str(e)}. Please correct and try again.', 'error')
        except GammuError as e:
            logger.error(f"Gammu error: {str(e)}")
            Message.update_status(message_id, 'failed')
            flash(f'System error: {str(e)}. Please try again later.', 'error')
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            Message.update_status(message_id, 'failed')
            flash('An unexpected error occurred. Please try again later.', 'error')
        
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