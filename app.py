"""
KEDARNATH TRAVEL - Complete All-in-One Backend Application
Developed by BITTU CHAUHAN

This script contains the full backend for the Kedarnath Travel website, 
including database models, API endpoints, and admin functionality.
"""

import os
import json
import random
import string
import secrets
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///kedarnath_travel.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Database Models
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    package = db.Column(db.String(50), nullable=False)
    persons = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='PENDING')
    booking_id = db.Column(db.String(20), unique=True)
    amount = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    special_requests = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'package': self.package,
            'persons': self.persons,
            'date': self.date.isoformat() if self.date else None,
            'status': self.status,
            'booking_id': self.booking_id,
            'amount': self.amount,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'special_requests': self.special_requests
        }

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'subject': self.subject,
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Create database tables if they don't exist
with app.app_context():
    try:
        db.create_all()
        print("Database tables created successfully.")
    except Exception as e:
        print(f"Error creating database tables: {e}")

# Helper Functions
def generate_booking_id():
    """Generate a unique booking ID."""
    prefix = 'KDR'
    random_digits = ''.join(random.choices(string.digits, k=8))
    timestamp = datetime.now().strftime('%H%M')
    booking_id = f"{prefix}{timestamp}{random_digits}"
    return booking_id

def calculate_package_amount(package, persons):
    """Calculate the total amount based on package and number of persons."""
    package_prices = {
        'Sacred Darshan': 19500,
        'Divine Journey': 32500,
        'Celestial Expedition': 58000
    }
    
    base_price = package_prices.get(package, 19500)
    return base_price * persons

# Routes
@app.route('/')
def index():
    """Render the main index page."""
    return render_template('index.html')

@app.route('/kedarnath-complete')
def kedarnath_complete():
    """Render the complete Kedarnath HTML content."""
    with open('frontend.html', 'r', encoding='utf-8') as file:
        html_content = file.read()
    return html_content

# API Routes
@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    """Get all bookings, sorted by creation date (most recent first)."""
    try:
        bookings = Booking.query.order_by(desc(Booking.created_at)).all()
        return jsonify([booking.to_dict() for booking in bookings]), 200
    except Exception as e:
        logger.error(f"Error fetching bookings: {e}")
        return jsonify({'message': 'Error fetching bookings', 'error': str(e)}), 500

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    """Create a new booking."""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['name', 'email', 'phone', 'package', 'date', 'persons']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        # Create new booking
        booking = Booking(
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            package=data['package'],
            persons=data['persons'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            booking_id=generate_booking_id(),
            amount=calculate_package_amount(data['package'], data['persons']),
            special_requests=data.get('special_requests', '')
        )
        
        db.session.add(booking)
        db.session.commit()
        
        return jsonify({
            'message': 'Booking created successfully',
            'booking_id': booking.booking_id,
            'booking': booking.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating booking: {e}")
        return jsonify({'message': 'Error creating booking', 'error': str(e)}), 500

@app.route('/api/bookings/<int:id>', methods=['PUT'])
def update_booking_status(id):
    """Update booking status."""
    try:
        booking = Booking.query.get(id)
        if not booking:
            return jsonify({'message': 'Booking not found'}), 404
        
        data = request.json
        if 'status' in data:
            booking.status = data['status']
            db.session.commit()
            return jsonify({
                'message': 'Booking status updated successfully',
                'booking': booking.to_dict()
            }), 200
        else:
            return jsonify({'message': 'Status field is required'}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating booking status: {e}")
        return jsonify({'message': 'Error updating booking status', 'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get booking statistics for admin dashboard."""
    try:
        total_bookings = Booking.query.count()
        confirmed_bookings = Booking.query.filter_by(status='CONFIRMED').count()
        pending_bookings = Booking.query.filter_by(status='PENDING').count()
        
        today = datetime.now().date()
        upcoming_bookings = Booking.query.filter(
            Booking.date >= today,
            Booking.status != 'CANCELED'
        ).count()
        
        total_revenue = db.session.query(db.func.sum(Booking.amount)).filter_by(status='CONFIRMED').scalar() or 0
        
        stats = {
            'total_bookings': total_bookings,
            'confirmed_bookings': confirmed_bookings,
            'pending_bookings': pending_bookings,
            'upcoming_bookings': upcoming_bookings,
            'total_revenue': float(total_revenue),
            'revenue_formatted': f'₹{total_revenue/100000:.1f}L' if total_revenue >= 100000 else f'₹{total_revenue:.2f}'
        }
        
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({'message': 'Error fetching stats', 'error': str(e)}), 500

@app.route('/api/contact', methods=['POST'])
def contact_form():
    """Handle contact form submissions."""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['name', 'email', 'subject', 'message']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Missing required field: {field}'}), 400
        
        # Create new contact submission
        contact = Contact(
            name=data['name'],
            email=data['email'],
            subject=data['subject'],
            message=data['message']
        )
        
        db.session.add(contact)
        db.session.commit()
        
        return jsonify({
            'message': 'Contact form submitted successfully'
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting contact form: {e}")
        return jsonify({'message': 'Error submitting contact form', 'error': str(e)}), 500

@app.route('/api/backup', methods=['GET'])
def backup_database():
    """Create a database backup."""
    try:
        bookings = Booking.query.all()
        contacts = Contact.query.all()
        
        backup_data = {
            'bookings': [booking.to_dict() for booking in bookings],
            'contacts': [contact.to_dict() for contact in contacts],
            'timestamp': datetime.utcnow().isoformat(),
            'backup_id': secrets.token_hex(8)
        }
        
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(backup_filename, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        return jsonify({
            'message': 'Database backup created successfully',
            'filename': backup_filename,
            'records': {
                'bookings': len(bookings),
                'contacts': len(contacts)
            }
        }), 200
    except Exception as e:
        logger.error(f"Error creating database backup: {e}")
        return jsonify({'message': 'Error creating database backup', 'error': str(e)}), 500

# Run the application
if __name__ == '__main__':
    # Make sure to bind to 0.0.0.0 instead of localhost
    # so the server is accessible from the browser
    app.run(host='0.0.0.0', port=5000, debug=True)