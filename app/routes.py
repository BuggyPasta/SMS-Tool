"""
Application routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from functools import wraps
from .models import User, Template, Message
from .database import get_db
from .services.gammu_service import GammuService
from .exceptions import GammuError, ModemError, SIMError, NetworkError, ErrorCode
import re
import logging
import time

# Initialize blueprints
auth_bp = Blueprint('auth', __name__)
admin_bp = Blueprint('admin', __name__)
user_bp = Blueprint('user', __name__)

# Get logger
logger = logging.getLogger('routes')

# Initialize GammuService singleton
gammu_service = GammuService()

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
        try:
            # Check database by executing a simple query
            try:
                db = get_db()
                db.execute('SELECT 1').fetchone()
                db_status = 'healthy'
            except Exception as e:
                logger.error(f"Database health check failed: {str(e)}")
                db_status = 'unhealthy'
            
            # Check modem
            try:
                modem_info = gammu_service.get_modem_info()
                modem_status = 'healthy' if modem_info else 'degraded'
                
                # Simplify modem info and extract only SIM7600E-H from the model string
                if modem_info:
                    model = modem_info.get('model', '')
                    # Extract just the SIM7600E-H part from the model string
                    if 'SIM7600E-H' in model:
                        model = 'SIM7600E-H'
                    elif 'SIMCOM_SIM7600E-H' in model:
                        model = 'SIM7600E-H'
                    # Remove any "unknown," prefix
                    model = model.replace('unknown,', '').strip()
                    modem_info = {
                        'signal': modem_info.get('signal', {}).get('SignalPercent'),
                        'model': model
                    }
            except Exception as e:
                logger.error(f"Modem health check failed: {str(e)}")
                modem_status = 'degraded'
                modem_info = None
            
            # Check SIM
            try:
                sim_info = gammu_service.get_sim_status()
                sim_status = 'healthy' if sim_info and sim_info.get('status') == 'ready' else 'degraded'
            except Exception as e:
                logger.error(f"SIM health check failed: {str(e)}")
                sim_status = 'degraded'
                sim_info = None
            
            # Overall health is healthy if database is working
            # We don't make the container unhealthy for modem, SIM or network issues
            status = 'healthy' if db_status == 'healthy' else 'unhealthy'
            
            response = {
                'status': status,
                'components': {
                    'database': {
                        'status': db_status
                    },
                    'modem': {
                        'status': modem_status,
                        'info': modem_info
                    },
                    'sim': {
                        'status': sim_status,
                        'info': sim_info
                    }
                }
            }
            
            return jsonify(response), 200 if status == 'healthy' else 500
        except Exception as e:
            logger.error(f"Health check error: {str(e)}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500

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
@auth_bp.route('/')
def root():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = User.get_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    if user['is_admin']:
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('user.dashboard'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.authenticate(username, password)
        if user:
            session['user_id'] = user['id']
            session['is_admin'] = user['is_admin']
            return redirect(url_for('admin.dashboard' if user['is_admin'] else 'user.dashboard'))
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

# Admin routes
@admin_bp.route('/')
@admin_required
def dashboard():
    try:
        templates = Template.get_all()
        messages = Message.get_all()
        return render_template('admin_dashboard.html',
                            templates=templates,
                            messages=messages)
    except Exception as e:
        logger.error(f"Error in admin dashboard: {str(e)}")
        flash('Error loading dashboard', 'error')
        return render_template('admin_dashboard.html',
                            templates=[],
                            messages=[])

@admin_bp.route('/users')
@admin_required
def manage_users():
    return render_template('manage_users.html')

@admin_bp.route('/users/add', methods=['GET', 'POST'])
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

@admin_bp.route('/users/delete', methods=['GET', 'POST'])
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

@admin_bp.route('/change_password', methods=['GET', 'POST'])
@admin_required
def change_password():
    try:
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
                return redirect(url_for('admin.dashboard'))
            else:
                flash('Failed to change password', 'error')
                return render_template('change_password.html')
    except Exception as e:
        logger.error(f"Error in change_password: {str(e)}")
        flash('An error occurred while changing the password', 'error')
        return render_template('change_password.html')
    
    return render_template('change_password.html')

@admin_bp.route('/manage-templates', methods=['GET', 'POST'])
@admin_required
def manage_templates():
    """Manage SMS templates"""
    if request.method == 'POST':
        action = request.form.get('action')
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title:
            return 'Missing required fields', 400
            
        if action == 'add':
            if not content:
                return 'Missing required fields', 400
            if Template.create(title, content):
                return 'Template created', 200
            return 'Failed to create template', 400
            
        elif action == 'update':
            if not content:
                return 'Missing required fields', 400
            if Template.update(title, content):
                return 'Template updated', 200
            return 'Failed to update template', 400
            
        elif action == 'delete':
            if title == 'Default':
                return 'Cannot delete default template', 400
            try:
                if Template.delete(title):
                    return 'Template deleted', 200
                return 'Failed to delete template', 400
            except Exception as e:
                logger.error(f"Error deleting template: {str(e)}")
                return 'Failed to delete template', 400
            
        return 'Invalid action', 400
    
    # GET request - show templates
    templates = Template.get_all()
    
    # If no templates exist, create the default template
    if not templates:
        default_content = "Hi, this is YOURNAMEHERE from COMPANY. Please do not reply to this message as it won't reach us. If you wish to contact us, please call 0123456789"
        Template.create('Default', default_content)
        templates = Template.get_all()
    
    return render_template('manage_templates.html', templates=templates)

@admin_bp.route('/report')
@admin_required
def sms_report():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    today = time.strftime('%Y-%m-%d')
    
    try:
        messages = Message.get_all(page, per_page)
        total_pages = Message.get_total_pages(per_page)
        
        # Convert messages to the format expected by the template
        reports = []
        for msg in messages:
            reports.append({
                'id': msg['id'],
                'date': msg['status_time'],
                'user': msg['sender_name'],
                'phone': msg['phone_number'],
                'status': msg['status'],
                'message': msg['content']
            })
        
        return render_template('sms_report.html',
                             reports=reports,
                             page=page,
                             total_pages=total_pages,
                             start_date=start_date,
                             end_date=end_date,
                             today=today)
    except Exception as e:
        logger.error(f"Error in SMS report: {str(e)}")
        flash('Error loading SMS report', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/report/delete/<int:message_id>', methods=['POST'])
@admin_required
def delete_message(message_id):
    if Message.delete(message_id):
        flash('Message deleted successfully', 'success')
    else:
        flash('Failed to delete message', 'error')
    return redirect(url_for('admin.sms_report'))

@admin_bp.route('/report/delete-all', methods=['POST'])
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
    try:
        templates = Template.get_all()
        return render_template('user_dashboard.html',
                            templates=templates)
    except Exception as e:
        logger.error(f"Error in user dashboard: {str(e)}")
        flash('Error loading dashboard', 'error')
        return render_template('user_dashboard.html',
                            templates=[])

@user_bp.route('/send-sms', methods=['POST'])
@login_required
def send_sms():
    """Send SMS message"""
    logger.info("Starting SMS send process")
    
    if not check_rate_limit():
        logger.warning("Rate limit exceeded")
        flash('Rate limit exceeded. Please try again later.', 'error')
        return redirect(url_for('user.dashboard'))

    phone_number = request.form.get('phone_number')
    message = request.form.get('message')
    
    logger.info(f"Attempting to send SMS to {phone_number}")
    
    # Validate phone number
    if not re.match(r'^07\d{9}$', phone_number):
        logger.warning(f"Invalid phone number format: {phone_number}")
        flash('Invalid phone number. Must start with 07 and be 11 digits long.', 'error')
        return redirect(url_for('user.dashboard'))
    
    # Check for repeated characters, excluding template placeholders (X's)
    if re.search(r'([^X])\1{3,}', message):
        logger.warning("Message contains too many repeated characters")
        flash('Message contains too many repeated characters. Please correct and try again.', 'error')
        return redirect(url_for('user.dashboard'))
    
    message_id = None
    try:
        # Create message record
        logger.info("Creating message record in database")
        message_id = Message.create(phone_number, message, session['user_id'])
        if not message_id:
            logger.error("Failed to create message record")
            flash('Failed to save message. Please try again.', 'error')
            return redirect(url_for('user.dashboard'))

        logger.info(f"Created message with ID: {message_id}")

        # Update status to sending
        logger.info("Updating message status to 'sending'")
        Message.update_status(message_id, 'sending')

        # Send message using GammuService singleton instance
        logger.info("Attempting to send message via Gammu")
        if gammu_service.send_sms(phone_number, message, message_id):
            logger.info(f"Successfully sent message {message_id}")
            Message.update_status(message_id, 'sent')
            flash('Message sent successfully', 'success')
        else:
            logger.error(f"Failed to send message {message_id}")
            Message.update_status(message_id, 'failed', 'Failed to send message')
            flash('Failed to send message. Please try again.', 'error')

    except ModemError as e:
        logger.error(f"Modem error sending message {message_id}: {str(e)}")
        if message_id:
            Message.update_status(message_id, 'failed', f"Modem error: {str(e)}")
        flash(f'Modem error: {str(e)}. Please check the modem connection.', 'error')
    except SIMError as e:
        logger.error(f"SIM error sending message {message_id}: {str(e)}")
        if message_id:
            Message.update_status(message_id, 'failed', f"SIM error: {str(e)}")
        flash(f'SIM card error: {str(e)}. Please check the SIM card.', 'error')
    except NetworkError as e:
        logger.error(f"Network error sending message {message_id}: {str(e)}")
        if message_id:
            Message.update_status(message_id, 'failed', f"Network error: {str(e)}")
        flash(f'Network error: {str(e)}. Please check the network connection.', 'error')
    except ValueError as e:
        logger.error(f"Validation error sending message {message_id}: {str(e)}")
        if message_id:
            Message.update_status(message_id, 'failed', f"Validation error: {str(e)}")
        flash(f'Message validation error: {str(e)}. Please correct and try again.', 'error')
    except GammuError as e:
        logger.error(f"Gammu error sending message {message_id}: {str(e)}")
        if message_id:
            Message.update_status(message_id, 'failed', f"Gammu error: {str(e)}")
        flash(f'System error: {str(e)}. Please try again later.', 'error')
    except Exception as e:
        logger.error(f"Unexpected error sending message {message_id}: {str(e)}, type: {type(e)}")
        logger.exception("Full traceback:")
        if message_id:
            Message.update_status(message_id, 'failed', f"Unexpected error: {str(e)}")
        flash('An unexpected error occurred. Please try again later.', 'error')
    
    logger.info("Finished SMS send process")
    return redirect(url_for('user.dashboard'))

@user_bp.route('/get-template/<title>')
@login_required
def get_template(title):
    template = Template.get_by_title(title)
    if template:
        return jsonify({'content': template['content']})
    return jsonify({'error': 'Template not found'}), 404 