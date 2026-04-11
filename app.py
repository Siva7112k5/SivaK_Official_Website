import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# SQLite Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Admin password from environment (default: admin123)
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# ---------- Database Model ----------
class ProjectRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    project_type = db.Column(db.String(50), nullable=False)
    plan = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    transaction_id = db.Column(db.String(200), nullable=False)
    payment_verified = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(50), default='pending_payment_verification')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'project_type': self.project_type,
            'plan': self.plan,
            'description': self.description,
            'transaction_id': self.transaction_id,
            'payment_verified': self.payment_verified,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Create tables (run once)
with app.app_context():
    db.create_all()

# ---------- Helper: Admin login required ----------
def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ---------- Routes ----------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit-request', methods=['POST'])
def submit_request():
    try:
        data = request.json
        required_fields = ['name', 'email', 'phone', 'project_type', 'plan', 'description', 'transaction_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'Missing field: {field}'}), 400

        new_request = ProjectRequest(
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            project_type=data['project_type'],
            plan=data['plan'],
            description=data['description'],
            transaction_id=data['transaction_id']
        )
        db.session.add(new_request)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Request submitted! Admin will verify payment soon.', 'id': new_request.id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error='Invalid password')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_login_required
def admin_dashboard():
    requests = ProjectRequest.query.order_by(ProjectRequest.created_at.desc()).all()
    return render_template('admin_dashboard.html', requests=[r.to_dict() for r in requests])

@app.route('/admin/verify-payment/<int:request_id>', methods=['POST'])
@admin_login_required
def verify_payment(request_id):
    try:
        req = ProjectRequest.query.get(request_id)
        if req:
            req.payment_verified = True
            req.status = 'payment_verified'
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Request not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/delete-request/<int:request_id>', methods=['POST'])
@admin_login_required
def delete_request(request_id):
    try:
        req = ProjectRequest.query.get(request_id)
        if req:
            db.session.delete(req)
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Request not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)