import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize Firebase Admin SDK
firebase_creds_json = os.environ.get('FIREBASE_CREDENTIALS_JSON')
if firebase_creds_json:
    cred_dict = json.loads(firebase_creds_json)
    cred = credentials.Certificate(cred_dict)
else:
    # For local development with a service account file (optional)
    cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'serviceAccountKey.json')
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
    else:
        raise Exception("Firebase credentials not found. Set FIREBASE_CREDENTIALS_JSON env var.")

firebase_admin.initialize_app(cred)
db = firestore.client()

# Admin password from environment (default: admin123)
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# Helper: login required decorator
def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

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
        
        # Create request document
        request_data = {
            'name': data['name'],
            'email': data['email'],
            'phone': data['phone'],
            'project_type': data['project_type'],
            'plan': data['plan'],
            'description': data['description'],
            'transaction_id': data['transaction_id'],
            'status': 'pending_payment_verification',  # admin will verify payment
            'created_at': datetime.utcnow().isoformat(),
            'payment_verified': False
        }
        doc_ref = db.collection('requests').add(request_data)
        return jsonify({'success': True, 'message': 'Request submitted! Admin will verify payment soon.', 'id': doc_ref[1].id})
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
    # Fetch all requests from Firestore
    requests_ref = db.collection('requests').order_by('created_at', direction=firestore.Query.DESCENDING)
    docs = requests_ref.stream()
    requests_list = []
    for doc in docs:
        req = doc.to_dict()
        req['id'] = doc.id
        requests_list.append(req)
    return render_template('admin_dashboard.html', requests=requests_list)

@app.route('/admin/verify-payment/<request_id>', methods=['POST'])
@admin_login_required
def verify_payment(request_id):
    try:
        doc_ref = db.collection('requests').document(request_id)
        doc = doc_ref.get()
        if doc.exists:
            doc_ref.update({'payment_verified': True, 'status': 'payment_verified'})
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Request not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/admin/delete-request/<request_id>', methods=['POST'])
@admin_login_required
def delete_request(request_id):
    try:
        db.collection('requests').document(request_id).delete()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)