from http.server import BaseHTTPRequestHandler
import json
import os
import re
import time
import traceback

# Try to import OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Get API key from environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if OPENAI_AVAILABLE and OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

# In-memory chat history (note: will reset on function cold start)
chat_history = {}

# Predefined answers
predefined_answers = {
    "what are the tuition fees": {
        "answer": """Okay, here are the full tuition and fee details for international and resident students at North American University:
International Undergraduate:
- Tuition per credit (1-11 credits): $1,125
- Tuition per semester (12-16 credits): $13,500
- Each additional credit over 16 credits: $1,125
- Summer Tuition per class: $873
Mandatory Fees per Semester:
- Departmental Fees: $55
- Computer & Internet Fees: $100
- Library Fee: $100
- Student Service Fee: $95
- Course with Lab Fee: $75
- Athletics Fee (Football, Basketball, Soccer): $1,050
- Athletics Fee (all other sports): $800
- Parking Fee (Covered/Uncovered): $80/$40
Estimated Total for International Undergraduate per Semester: $16,826
Resident Undergraduate:
- Tuition per credit (1-11 credits): $614
- Tuition per semester (12-16 credits): $7,368
- Each additional credit over 16 credits: $614
- Summer Tuition per class: $873
Mandatory Fees per Semester: 
- Departmental Fees: $55
- Computer & Internet Fees: $100
- Library Fee: $100
- Student Service Fee: $95
- Course with Lab Fee: $75
- Athletics Fee (Football, Basketball, Soccer): $1,050
- Athletics Fee (all other sports): $800
- Parking Fee (Covered/Uncovered): $80/$40
Estimated Total for Resident Undergraduate per Semester: $10,133""",
        "sources": ["https://www.na.edu/admissions/tuition-and-fees/"]
    },
    "how do i apply for admission": {
        "answer": """Here are the steps to apply to North American University:
1. Create and submit an application online at https://apply.na.edu/admission
2. Pay the application fee ($75 USD)
3. Submit required documents:
   - Copy of Passport
   - Academic Credentials & Test Scores
   - Certificate of Finances (COF)
   - Affidavit of Support (if applicable)""",
        "sources": ["https://www.na.edu/admissions/"]
    },
    "what programs does nau offer": {
        "answer": """North American University offers these programs:
Undergraduate Programs:
- Bachelor of Business Administration (BBA)
- Bachelor of Science in Computer Science (BS)
- Bachelor of Science in Criminal Justice (BS)
- Bachelor of Science in Education (BS)
Graduate Programs:
- Master of Business Administration (MBA)
- Master of Science in Computer Science (MS)
- Master of Education (M.Ed.) in Curriculum and Instruction
- Master of Education (M.Ed.) in Educational Leadership""",
        "sources": ["https://www.na.edu/academics/"]
    }
}

# Exact match patterns for the predefined questions
EXACT_MATCHES = {
    "what are the tuition fees": ["tuition fees", "what are the tuition and fees", "how much is tuition"],
    "how do i apply for admission": ["how do i apply", "application process", "how to apply"],
    "what programs does nau offer": ["programs offered", "available degrees", "majors", "degree programs"]
}

# Function to find a predefined answer for a query
def get_predefined_answer(query):
    # Clean and normalize the query
    clean_query = re.sub(r'[^\w\s]', '', query.lower().strip())
    
    # Check for direct match first
    if clean_query in predefined_answers:
        return predefined_answers[clean_query]
    
    # Check for match in patterns
    for key, patterns in EXACT_MATCHES.items():
        for pattern in patterns:
            if pattern in clean_query:
                return predefined_answers[key]
    
    # No match found
    return None

# Create a minimal knowledge base
def create_minimal_knowledge_base():
    knowledge = [
        {
            "content": "North American University (NAU) is a private, non-profit university located in Stafford, Texas.",
            "source": "https://www.na.edu/about/"
        },
        {
            "content": "Tuition for international undergraduate students at North American University is $1,125 per credit.",
            "source": "https://www.na.edu/admissions/tuition-and-fees/"
        }
    ]
    return knowledge

# Process a chat request
def process_chat_request(data):
    try:
        chat_id = data.get('chat_id', 'default')
        query = data.get('query', '')
        
        if not query:
            return {"error": "Query is required"}, 400
        
        # Initialize chat history if it doesn't exist
        if chat_id not in chat_history:
            chat_history[chat_id] = []
        
        # Add user message to history
        chat_history[chat_id].append({
            "role": "user",
            "content": query,
            "timestamp": time.time()
        })
        
        # Check for predefined answers first
        predefined = get_predefined_answer(query)
        if predefined:
            answer = predefined["answer"]
            sources = predefined.get("sources", ["https://www.na.edu"])
            
            # Add assistant message to history
            chat_history[chat_id].append({
                "role": "assistant",
                "content": answer,
                "sources": sources,
                "timestamp": time.time()
            })
            
            return {
                "answer": answer,
                "sources": sources,
                "chat_id": chat_id
            }, 200
            
        else:
            # Generate a simple response without OpenAI
            default_answer = "Thank you for your question about North American University. For the most accurate information, please visit https://www.na.edu or contact the admissions office at admissions@na.edu."
            sources = ["https://www.na.edu"]
            
            # Add assistant message to history
            chat_history[chat_id].append({
                "role": "assistant",
                "content": default_answer,
                "sources": sources,
                "timestamp": time.time()
            })
            
            return {
                "answer": default_answer,
                "sources": sources,
                "chat_id": chat_id
            }, 200
    
    except Exception as e:
        print(f"Error processing query: {str(e)}")
        print(traceback.format_exc())
        return {"error": f"Server error: {str(e)}"}, 500

# Define handler for Vercel
class handler(BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200, content_type='application/json'):
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type, Accept')
        self.end_headers()
    
    def do_OPTIONS(self):
        self._set_headers()
    
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            if self.path == '/api/chat':
                response, status_code = process_chat_request(data)
                self._set_headers(status_code)
                self.wfile.write(json.dumps(response).encode())
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Not found"}).encode())
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_GET(self):
        self._set_headers(200)
        self.wfile.write(json.dumps({"status": "API is running"}).encode())