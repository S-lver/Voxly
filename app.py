import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, Response
from flask_sqlalchemy import SQLAlchemy
from services.gemini_service import GeminiService
from services.excel_service import ExcelService
from config import Config
import json
import logging
from datetime import datetime, timedelta
import csv
from io import StringIO
import uuid
import re

# ============================================
# IMPORT MODELS - FIXES THE NameError
# ============================================
from models import db, Student, CallLog

app = Flask(__name__)

# Create instance directory
os.makedirs('instance', exist_ok=True)

app.config.from_object(Config)

# db is now imported from models, so don't redefine it here
# Just make sure it's initialized with the app
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()
    print("✅ Database ready")

# Initialize services
gemini = GeminiService()
excel_service = ExcelService()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversations store
conversations = {}

# ============================================
# ROUTES
# ============================================

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/call')
def call_simulator():
    try:
        students = Student.query.all()
        return render_template('call_simulator.html', students=students)
    except Exception as e:
        print(f"❌ Error in call_simulator: {e}")
        return render_template('call_simulator.html', students=[])

@app.route('/logs')
def logs():
    return render_template('call_logs.html')

# ============================================
# API ROUTES
# ============================================

@app.route('/api/upload', methods=['POST'])
def upload_excel():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({'error': 'Please upload an Excel file (.xlsx or .xls)'}), 400
    
    try:
        filepath = excel_service.save_file(file)
        result = excel_service.process_students(filepath)
        
        if result.get('error'):
            return jsonify({'error': result['error']}), 400
        
        return jsonify({
            'success': True,
            'message': f'Successfully added {result["students_added"]} students!',
            'students_added': result['students_added']
        })
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download_sample')
def download_sample():
    filepath = excel_service.export_sample()
    return send_file(filepath, as_attachment=True, download_name='sample_students.xlsx')

@app.route('/api/call/start', methods=['POST'])
def start_call():
    session_id = str(uuid.uuid4())[:8]
    student_name = request.json.get('student')
    
    conversations[session_id] = {
        'history': [],
        'student': student_name,
        'student_data': None,
        'started_at': datetime.now(),
        'resolved': None,
        'ended': False,
        'awaiting_feedback': False
    }
    
    if student_name:
        student = Student.query.filter_by(name=student_name).first()
        if student:
            conversations[session_id]['student_data'] = {
                'Name': student.name,
                'Grade': student.grade,
                'Homeroom': student.homeroom,
                'Balance': f'${student.balance:.2f}',
                'Attendance': student.attendance,
                'Email': student.email,
                'Registered': 'Yes'
            }
    
    greeting = "Hello! Welcome to EduCall AI School Assistant. How can I help you today?"
    
    return jsonify({
        'session_id': session_id,
        'response': greeting,
        'student': student_name
    })

@app.route('/api/call/message', methods=['POST'])
def send_message():
    data = request.json
    session_id = data.get('session_id')
    user_message = data.get('message')
    
    if session_id not in conversations:
        return jsonify({'error': 'Session not found'}), 404
    
    session = conversations[session_id]
    session['history'].append({'role': 'user', 'content': user_message})
    
    if session.get('ended'):
        return jsonify({
            'response': 'This call has ended. Please start a new call.',
            'ended': True
        })
    
    if session.get('awaiting_feedback'):
        if 'yes' in user_message.lower() or 'resolved' in user_message.lower():
            session['resolved'] = True
            session['user_feedback'] = 'resolved'
            session['ended'] = True
            _save_call_log(session, session_id)
            return jsonify({
                'response': "I'm so glad we could resolve your issue today! Have a great day!",
                'ended': True,
                'resolved': True
            })
        elif 'no' in user_message.lower() or 'unresolved' in user_message.lower() or 'not' in user_message.lower():
            session['resolved'] = False
            session['user_feedback'] = 'unresolved'
            session['ended'] = True
            _save_call_log(session, session_id)
            return jsonify({
                'response': "I'm sorry we couldn't resolve your issue. I'm transferring you to a human agent now. Please hold.",
                'ended': True,
                'resolved': False,
                'transfer': True
            })
        else:
            return jsonify({
                'response': "I just need a quick yes or no - was your issue resolved today?",
                'awaiting_feedback': True
            })
    
    student_name = session.get('student')
    if not student_name:
        name_patterns = [
            r'(?:my (?:son|daughter|child|student) (?:is|called) )([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)',
            r'(?:about |for )([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)',
            r'(?:student )([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)',
        ]
        for pattern in name_patterns:
            match = re.search(pattern, user_message, re.IGNORECASE)
            if match:
                student_name = match.group(1)
                break
    
    student_data = session.get('student_data')
    history = session['history'][:-1]
    
    ai_response = gemini.get_response(
        user_message,
        student_data=student_data,
        conversation_history=history,
        student_name=student_name
    )
    
    session['history'].append({'role': 'assistant', 'content': ai_response})
    
    if 'resolved' in ai_response.lower() or 'was your issue resolved' in ai_response.lower():
        session['awaiting_feedback'] = True
        return jsonify({
            'response': ai_response,
            'awaiting_feedback': True
        })
    
    if any(word in user_message.lower() for word in ['goodbye', 'bye', 'thank you', 'thanks', 'done', 'that\'s all']):
        session['awaiting_feedback'] = True
        return jsonify({
            'response': ai_response + " Before you go, was your issue resolved today?",
            'awaiting_feedback': True
        })
    
    return jsonify({
        'response': ai_response,
        'awaiting_feedback': False
    })

@app.route('/api/call/end', methods=['POST'])
def end_call():
    data = request.json
    session_id = data.get('session_id')
    
    if session_id in conversations:
        session = conversations[session_id]
        session['ended'] = True
        
        if session.get('resolved') is None:
            _save_call_log(session, session_id)
        
        return jsonify({'success': True})
    
    return jsonify({'error': 'Session not found'}), 404

def _save_call_log(session, session_id):
    try:
        question = None
        for msg in session['history']:
            if msg['role'] == 'user':
                question = msg['content']
                break
        
        response = None
        for msg in session['history']:
            if msg['role'] == 'assistant':
                response = msg['content']
                break
        
        call_log = CallLog(
            session_id=session_id,
            student_name=session.get('student', ''),
            question=question,
            ai_response=response,
            resolved=session.get('resolved'),
            user_feedback=session.get('user_feedback'),
            duration=int((datetime.now() - session.get('started_at', datetime.now())).total_seconds())
        )
        db.session.add(call_log)
        db.session.commit()
        
    except Exception as e:
        logger.error(f"Error saving call log: {e}")

# ============================================
# API FOR LOGS
# ============================================

@app.route('/api/logs', methods=['GET'])
def get_logs():
    logs = CallLog.query.order_by(CallLog.created_at.desc()).all()
    return jsonify([log.to_dict() for log in logs])

@app.route('/api/logs/resolved', methods=['GET'])
def get_resolved_logs():
    logs = CallLog.query.filter_by(resolved=True).order_by(CallLog.created_at.desc()).all()
    return jsonify([log.to_dict() for log in logs])

@app.route('/api/logs/unresolved', methods=['GET'])
def get_unresolved_logs():
    logs = CallLog.query.filter_by(resolved=False).order_by(CallLog.created_at.desc()).all()
    return jsonify([log.to_dict() for log in logs])

@app.route('/api/logs/export', methods=['GET'])
def export_logs():
    logs = CallLog.query.order_by(CallLog.created_at.desc()).all()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Student', 'Question', 'AI Response', 'Resolved', 'Duration'])
    
    for log in logs:
        writer.writerow([
            log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            log.student_name,
            log.question,
            log.ai_response,
            'Yes' if log.resolved else 'No' if log.resolved is not None else 'Not Asked',
            f'{log.duration}s'
        ])
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=call_logs.csv'}
    )

@app.route('/api/students', methods=['GET'])
def get_students():
    students = Student.query.all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'grade': s.grade,
        'homeroom': s.homeroom,
        'parent_phone': s.parent_phone,
        'balance': s.balance,
        'attendance': s.attendance,
        'email': s.email
    } for s in students])

@app.route('/api/students', methods=['DELETE'])
def delete_students():
    try:
        db.session.query(Student).delete()
        db.session.commit()
        return jsonify({'success': True, 'message': 'All students deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        total_calls = CallLog.query.count()
        resolved = CallLog.query.filter_by(resolved=True).count()
        unresolved = CallLog.query.filter_by(resolved=False).count()
        not_asked = CallLog.query.filter_by(resolved=None).count()
        
        return jsonify({
            'total_calls': total_calls,
            'resolved': resolved,
            'unresolved': unresolved,
            'not_asked': not_asked,
            'resolution_rate': f"{(resolved / total_calls * 100) if total_calls > 0 else 0:.1f}%",
            'total_students': Student.query.count()
        })
    except Exception as e:
        print(f"❌ Stats error: {e}")
        return jsonify({
            'total_calls': 0,
            'resolved': 0,
            'unresolved': 0,
            'not_asked': 0,
            'resolution_rate': '0%',
            'total_students': 0
        })

# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
