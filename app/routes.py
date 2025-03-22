"""
Application routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from functools import wraps
from .models import User, Template, Message, get_db
from .services.gammu_service import GammuService
from .exceptions import GammuError, ModemError, SIMError, NetworkError, ErrorCode
import re
import logging
import time
from . import gammu_service

# Initialize blueprints
auth_bp = Blueprint('auth', __name__)
admin_bp = Blueprint('admin', __name__)
user_bp = Blueprint('user', __name__)

# Get logger
logger = logging.getLogger('routes')

# Rate limiting configuration
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 30
rate_limit_data = {
    'requests': [],
    'window_start': time.time()
}

def check_rate_limit():
    """Check if request is within rate limits"""
    current_time = time.time()
    
    # Clear old requests
    rate_limit_data['requests'] = [
        req_time for req_time in rate_limit_data['requests']
        if current_time - req_time < RATE_LIMIT_WINDOW
    ]
    
    # Check if window has expired
    if current_time - rate_limit_data['window_start'] >= RATE_LIMIT_WINDOW:
        rate_limit_data['window_start'] = current_time
        rate_limit_data['requests'] = []
    
    # Check if limit exceeded
    if len(rate_limit_data['requests']) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    
    # Add current request
    rate_limit_data['requests'].append(current_time)
    return True

def standardize_health_response(status: str, components: dict = None, error: str = None) -> tuple:
    """Create standardized health check response"""
    response = {
        'status': status,
        'timestamp': time.time(),
        'components': components or {}
    }
    
    if error:
        response['error'] = error
    
    status_code = 200 if status == 'healthy' else 500
    return jsonify(response), status_code

def register_health_check(app):
    """Register health check endpoint directly on the app"""
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        logger.debug("Running health check")
        components = {}
        overall_status = 'healthy'

        try:
            # Get modem info
            logger.debug("Checking modem health")
            try:
                modem_info = gammu_service.get_modem_info()
                components['modem'] = {
                    'status': 'healthy',
                    'info': modem_info
                }
                logger.debug("Modem health check passed")
            except Exception as e:
                logger.warning(f"Modem health check degraded: {e}")
                components['modem'] = {
                    'status': 'degraded',
                    'error': str(e)
                }
                overall_status = 'degraded'

            # Get SIM status
            logger.debug("Checking SIM health")
            try:
                sim_info = gammu_service.get_sim_status()
                components['sim'] = {
                    'status': 'healthy' if sim_info['status'] == 'ready' else 'degraded',
                    'info': sim_info
                }
                if sim_info['status'] != 'ready':
                    overall_status = 'degraded'
                logger.debug("SIM health check completed")
            except Exception as e:
                logger.warning(f"SIM health check degraded: {e}")
                components['sim'] = {
                    'status': 'degraded',
                    'error': str(e)
                }
                overall_status = 'degraded'

            # Get network status
            logger.debug("Checking network health")
            try:
                network_info = gammu_service.get_network_status()
                components['network'] = {
                    'status': 'healthy',
                    'info': network_info
                }
                logger.debug("Network health check passed")
            except Exception as e:
                logger.warning(f"Network health check degraded: {e}")
                components['network'] = {
                    'status': 'degraded',
                    'error': str(e)
                }
                overall_status = 'degraded'

            return standardize_health_response(overall_status, components)

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return standardize_health_response('unhealthy', {
                'error': str(e)
            })

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
            session['user_id'] = user['id']
            session['is_admin'] = user['is_admin']
            if user['is_admin'] and user['password'] == 'admin':
                session['password_warning'] = True
                flash('Please change your default admin password!', 'warning')
            return redirect(url_for('admin.dashboard' if user['is_admin'] else 'user.dashboard'))
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

@admin_bp.route('/admin/users')
@admin_required
def manage_users():
    return render_template('manage_users.html')

@admin_bp.route('/admin/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if len(username) < 2 or len(password) < 2:
            flash('Username and password must be at least 2 characters long', 'error')
            return render_template('add_user.html')
        
        if User.create(username, password):
            flash('User added successfully', 'success')
            return redirect(url_for('admin.manage_users'))
        else:
            flash('Username already exists', 'error')
            return render_template('add_user.html')
    
    return render_template('add_user.html')

@admin_bp.route('/admin/users/delete', methods=['GET', 'POST'])
@admin_required
def delete_user():
    if request.method == 'POST':
        username = request.form.get('username')
        if username == 'admin':
            flash('Cannot delete admin user', 'error')
            return redirect(url_for('admin.delete_user'))
        
        if User.delete(username):
            flash('User deleted successfully', 'success')
            return redirect(url_for('admin.manage_users'))
        else:
            flash('Failed to delete user', 'error')
            return redirect(url_for('admin.delete_user'))
    
    users = User.get_all()
    return render_template('delete_user.html', users=users)

@admin_bp.route('/admin/change_password', methods=['GET', 'POST'])
@admin_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_password or not new_password or not confirm_password:
            flash('All fields are required', 'error')
            return render_template('change_password.html')
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return render_template('change_password.html')
        
        if len(new_password) < 2:
            flash('Password must be at least 2 characters long', 'error')
            return render_template('change_password.html')
        
        user = User.get_by_id(session['user_id'])
        if not user or not User.authenticate(user['username'], current_password):
            flash('Current password is incorrect', 'error')
            return render_template('change_password.html')
        
        if User.update_password(user['username'], new_password):
            flash('Password changed successfully', 'success')
            session.pop('password_warning', None)  # Remove password warning after change
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Failed to change password', 'error')
            return render_template('change_password.html')
    
    return render_template('change_password.html')

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
        
        message_id = None
        try:
            # Create message record
            message_id = Message.create(phone_number, message, session['user_id'])
            if not message_id:
                flash('Failed to save message. Please try again.', 'error')
                return redirect(url_for('user.send_sms'))

            # Send message
            if gammu_service.send_sms(phone_number, message, message_id):
                Message.update_status(message_id, 'sent')
                flash('Message sent successfully', 'success')
            else:
                Message.update_status(message_id, 'failed')
                flash('Failed to send message. Please try again.', 'error')

        except ModemError as e:
            logger.error(f"Modem error: {str(e)}")
            if message_id:
                Message.update_status(message_id, 'failed', str(e))
            flash(f'Modem error: {str(e)}. Please check the modem connection.', 'error')
        except SIMError as e:
            logger.error(f"SIM error: {str(e)}")
            if message_id:
                Message.update_status(message_id, 'failed', str(e))
            flash(f'SIM card error: {str(e)}. Please check the SIM card.', 'error')
        except NetworkError as e:
            logger.error(f"Network error: {str(e)}")
            if message_id:
                Message.update_status(message_id, 'failed', str(e))
            flash(f'Network error: {str(e)}. Please check the network connection.', 'error')
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            if message_id:
                Message.update_status(message_id, 'failed', str(e))
            flash(f'Message validation error: {str(e)}. Please correct and try again.', 'error')
        except GammuError as e:
            logger.error(f"Gammu error: {str(e)}")
            if message_id:
                Message.update_status(message_id, 'failed', str(e))
            flash(f'System error: {str(e)}. Please try again later.', 'error')
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            if message_id:
                Message.update_status(message_id, 'failed', str(e))
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