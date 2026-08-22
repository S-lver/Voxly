import os
from google import genai
from models import Student

class GeminiService:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = "gemini-3.6-flash"
    
    def get_student_info(self, student_name):
        if not student_name:
            return None
        
        student = Student.query.filter_by(name=student_name).first()
        if student:
            return {
                'name': student.name,
                'grade': student.grade,
                'homeroom': student.homeroom,
                'balance': f'${student.balance:.2f}',
                'attendance': student.attendance,
                'email': student.email,
                'parent_phone': student.parent_phone,
                'registered': True
            }
        
        students = Student.query.filter(Student.name.ilike(f'%{student_name}%')).all()
        if students:
            return [{
                'name': s.name,
                'grade': s.grade,
                'homeroom': s.homeroom,
                'balance': f'${s.balance:.2f}',
                'attendance': s.attendance,
                'email': s.email,
                'parent_phone': s.parent_phone,
                'registered': True
            } for s in students]
        
        return {'registered': False, 'message': f'No student found with name: {student_name}'}
    
    def get_response(self, user_message, student_data=None, conversation_history=None, student_name=None):
        student_info = None
        if student_name:
            student_info = self.get_student_info(student_name)
        
        system_prompt = """You are a friendly and professional school call center agent named EduCall.

Your personality:
- Warm, helpful, and patient
- Speak clearly and concisely
- Always confirm you've understood

Your capabilities:
1. Check student lunch balances and payment history
2. Report attendance (today, week, month)
3. List upcoming school events
4. Check student registration status
5. Send payment links via SMS
6. Transfer to human staff when needed

Rules:
- If you don't know something, be honest and offer to transfer
- Always ask at the end: "Was your issue resolved today? Yes or No?"
- If they say no, ask: "What else can I help you with?"
- Keep responses conversational and natural

Always end with: "Is there anything else I can help you with?" or "Was your issue resolved?"""

        if student_info:
            if isinstance(student_info, list):
                context = "\n\nStudent Search Results:\n"
                for s in student_info:
                    context += f"- {s['name']} (Grade {s['grade']}, Homeroom: {s['homeroom']}, Balance: {s['balance']})\n"
                context += "\nLet the user know multiple students were found and ask which one they're asking about."
            elif student_info.get('registered'):
                context = "\n\nStudent Information:\n"
                for key, value in student_info.items():
                    if key != 'registered':
                        context += f"- {key}: {value}\n"
                context += "\nThis student IS registered at this school. Confirm their registration status and offer to check other info (balance, attendance, etc.)"
            else:
                context = f"\n\nStudent Lookup Result: {student_info.get('message', 'Student not found')}\n"
                context += "Let the user know this student is not in the system. Offer to transfer to the registration office."
            
            system_prompt += context
        
        if student_data:
            context = "\n\nAdditional Student Information:\n"
            for key, value in student_data.items():
                if value:
                    context += f"- {key}: {value}\n"
            system_prompt += context
        
        conversation = ""
        if conversation_history:
            for msg in conversation_history:
                role = "User" if msg['role'] == 'user' else "Assistant"
                conversation += f"{role}: {msg['content']}\n"
        
        full_prompt = f"{system_prompt}\n\n{conversation}User: {user_message}\nAssistant:"
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt,
                config={
                    "temperature": 0.7,
                    "max_output_tokens": 1024,
                    "top_p": 0.95,
                    "top_k": 40,
                }
            )
            return response.text.strip()
        except Exception as e:
            print(f"Gemini error: {e}")
            return "I'm having trouble connecting right now. Let me transfer you to a staff member."