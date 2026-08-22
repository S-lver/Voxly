from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.String(10))
    homeroom = db.Column(db.String(50))
    parent_phone = db.Column(db.String(20))
    balance = db.Column(db.Float, default=0.0)
    attendance = db.Column(db.String(20), default='Present')
    email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CallLog(db.Model):
    __tablename__ = 'call_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50))
    student_name = db.Column(db.String(100))
    question = db.Column(db.Text)
    ai_response = db.Column(db.Text)
    resolved = db.Column(db.Boolean, default=None)
    user_feedback = db.Column(db.String(20))
    duration = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'student_name': self.student_name,
            'question': self.question,
            'ai_response': self.ai_response,
            'resolved': self.resolved,
            'user_feedback': self.user_feedback,
            'duration': self.duration,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }