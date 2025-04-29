from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
import time
import re
import asyncio
import functools
from dotenv import load_dotenv
from openai import OpenAI
# Async support for Flask
from asgiref.sync import async_to_sync

# Set up logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def make_async_compatible(app):
    """
    Wraps Flask routes with async support using asgiref.
    This allows async functions to be used in Flask routes.
    """
    original_route = app.route
    
    def async_route(rule, **options):
        def decorator(func):
            if not asyncio.iscoroutinefunction(func):
                return original_route(rule, **options)(func)
                
            @original_route(rule, **options)
            @functools.wraps(func)
            def sync_func(*args, **kwargs):
                return async_to_sync(func)(*args, **kwargs)
                
            return sync_func
            
        return decorator
        
    app.route = async_route
    
    return app

app = Flask(__name__)
app = make_async_compatible(app)
CORS(app)

# Configure OpenAI client
load_dotenv()

# Get API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY environment variable. Please set it in your .env file.")

# Predefined answers for frequently asked questions (including exact match keys and follow-ups)
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
Estimated Total for Resident Undergraduate per Semester: $10,133
International Graduate:
- Tuition per credit: 
  - MBA: $658
  - MS Computer Science: $732
  - M.Ed. Programs: $511
- Total Tuition (30 credits):
  - MBA: $19,740
  - MS Computer Science: $21,960
  - M.Ed. Programs: $15,330
Resident Graduate:
- Tuition per credit:
  - MBA: $402
  - MS Computer Science: $402
  - M.Ed. Programs: $326
- Total Tuition (30 credits): 
  - MBA: $12,060
  - MS Computer Science: $12,060
  - M.Ed. Programs: $9,780
Let me know if you need any clarification or have additional questions!""",
        "sources": ["https://www.na.edu/admissions/tuition-and-fees/"],
        "follow_up": {
            "question": "Are you planning to use on-campus housing as well?",
            "yes_response": """Great! Here's the housing and meal plan information:

Housing Options:
- Housing On Campus 2 Bed-Room only for men: $2,500.00 per semester
- Housing On Campus 3 Bed-Room only for men: $2,100.00 per semester
- Housing On Campus 4 Bed-Room only for men: $1,900.00 per semester
- Housing on Hotel 2 Bed-Room: $3,600.00 per semester
- Housing on Hotel 3 Bedroom: $3,000.00 per semester
- Housing on Apartment 2 Bedroom: $3,200.00 per semester
- Summer Housing: $1,250.00

Additional Housing Fees:
- Housing Deposit Fee: $150.00
- Housing Application Fee: $50.00

Meal Service Options:
- 19-Meal per Week: $2,500.00 per semester
- 14-Meal per Week: $1,900.00 per semester
- 10-Meal per Week: $1,300.00 per semester

Note: Housing is first-come, first-served.

This brings your total estimated costs to:
- Tuition: $13,500 per semester (12-16 credits)
- Housing (varies by option): $1,900 - $3,600 per semester
- Meal Plan (varies by option): $1,300 - $2,500 per semester
- Mandatory Fees: Approximately $450

Would you like more specific information about any housing options?""",
            "no_response": """No problem! If you ever need information about housing or other campus services in the future, feel free to ask.

Is there anything else you'd like to know about North American University?"""
        }
    },
    "how do i apply for admission": {
        "answer": """Okay, here are the steps to apply to North American University as an international student:
STEP 1: Create and submit application
- Create your NAU Account at https://apply.na.edu/admission and submit a completed application online.
STEP 2: Pay application fee* ($75 USD)
- Please select to make the payment online via Credit Card or an International Wire Transfer by accessing NAU's wire transfer banking information.
STEP 3: Send Required Documents
In order to obtain admission to NAU, an international student must submit the following documents by the application deadlines. All application documents should be properly scanned and emailed in PDF format to intadmissions@na.edu:
1. Copy of Passport: Only the photograph and visa (when received) page are necessary.
2. Official Academic Credentials & Test Scores: 
- Official Copy of the High School Diploma Evaluation (The transcript has to be evaluated at one of the agencies listed on the website)
- Official SAT/ACT, official TOEFL or official IELTS scores.
3. Certificate of Finances (COF): This form demonstrates that you have sufficient funds to cover the cost of tuition, fees, and living expenses for at least the first year of study.
4. Affidavit of Support (if applicable): If you will be sponsored by family or another individual, they will need to complete this form.
Let me know if you have any other questions about the application process!""",
        "sources": ["https://www.na.edu/admissions/"],
        "follow_up": {
            "question": "Are you applying as an undergraduate or graduate student?",
            "undergraduate_response": """Great! For undergraduate admission, you'll also need to provide:

1. High school transcripts (evaluated by a credential evaluation service)
2. English proficiency test scores (TOEFL: minimum 61, IELTS: minimum 5.5)
3. SAT/ACT scores (optional but recommended for scholarship consideration)

The application deadlines are:
- Fall semester: August 1
- Spring semester: December 15
- Summer semester: May 1

Would you like more specific information about any of the undergraduate programs?""",
            "graduate_response": """Excellent! For graduate admission, you'll need these additional documents:

1. Bachelor's degree transcripts (evaluated by a credential evaluation service)
2. English proficiency test scores (TOEFL: minimum 79, IELTS: minimum 6.5)
3. Statement of Purpose
4. Two letters of recommendation
5. Resume/CV
6. GRE/GMAT scores (required for some programs)

The application deadlines are:
- Fall semester: July 15
- Spring semester: December 1
- Summer semester: April 15

Is there a specific graduate program you're interested in learning more about?"""
        }
    },
    "what programs does nau offer": {
        "answer": """North American University offers the following undergraduate and graduate degree programs:
Undergraduate Programs:
- Bachelor of Business Administration (BBA)
- Bachelor of Science in Computer Science (BS)
- Bachelor of Science in Criminal Justice (BS)
- Bachelor of Science in Education (BS)
Graduate Programs:
- Master of Business Administration (MBA)
- Master of Science in Computer Science (MS)
- Master of Education (M.Ed.) in Curriculum and Instruction
- Master of Education (M.Ed.) in Educational Leadership
In addition, NAU also offers the following programs:
Language Programs:
- Intensive English Program (IEP)
- English as a Second Language (ESL)
Educator Certification Programs:
- Teacher Certification
- Principal Certification
- Superintendent Certification
Continuing Education Programs:
- Professional Development Courses
- Certificate Programs
The university is committed to providing a well-rounded education that prepares students for successful careers. The degree programs are designed to develop critical thinking, problem-solving, and leadership skills.
Let me know if you'd like more information about any specific program!""",
        "sources": ["https://www.na.edu/academics/"],
        "follow_up": {
            "question": "Which program are you most interested in learning more about?",
            "custom_response": True
        }
    },
    "how to reset my password": {
        "answer": """Okay, here are the steps to reset your password for your North American University account:
1. Go to the password reset page at https://passwordreset.microsoftonline.com/
2. Enter your NAU username (usually the first initial of your first name followed by your last name, e.g. jsmith@na.edu)
3. Enter the characters shown in the image to verify you are not a robot.
4. Select "Email" as the contact method for verification.
5. Check your email for a verification code and enter it on the next page.
6. Create a new password, confirm it, and click "Finish".
7. Once your password has been successfully reset, you can sign in to your NAU account with the new password.
A few important things to note:
- You need to complete the reset process within 60 minutes of initiating it.
- Make sure to update the new password on any devices or email programs you use to access your NAU account.
- If you have any trouble with the reset process, you can contact the IT Helpdesk at support@na.edu or 832-230-5541 for assistance.
Let me know if you have any other questions!""",
        "sources": ["https://www.na.edu/it-services/"]
    },
    "how do i select the courses": {
        "answer": """Okay, here are the steps to select and register for courses at North American University:
1. Meet with your Academic Advisor
- Schedule an appointment with your assigned academic advisor to discuss your degree plan and course options.
- Your advisor can help you select the appropriate courses based on your major, prerequisites, and academic progress.
2. Review the Course Catalog
- Familiarize yourself with the course descriptions, prerequisites, and schedules in the university's course catalog.
- Make a list of the courses you need to take and any electives you're interested in.
3. Register for Courses
- Log into your MyNAU student portal at https://portal.na.edu
- Navigate to the "Registration" section and select "Course Search"
- Use the filters to find available sections of the courses you need
- Add the courses to your shopping cart and complete the registration process
4. Finalize Your Schedule
- Review your schedule to ensure you've registered for the correct courses and credit hours.
- Make any necessary adjustments by adding or dropping courses during the add/drop period.
- Confirm your final schedule and tuition charges on your student account.
5. Attend Courses
- Attend all scheduled class sessions and actively participate.
- Complete all assignments, projects, and exams as required for each course.
Let me know if you have any other questions about the course selection and registration process!""",
        "sources": ["https://www.na.edu/academics/registration/"],
        "follow_up": {
            "question": "Do you need help with checking course availability for the upcoming semester?",
            "yes_response": """To check course availability:

1. Log into your MyNAU portal at https://portal.na.edu
2. Go to the "Student" tab
3. Click on "Course Search"
4. Select the upcoming term from the dropdown menu
5. You can search by:
   - Course Number (e.g., CS 1301)
   - Subject (e.g., Computer Science)
   - Meeting Time (if you have specific scheduling needs)
   - Instructor (if you prefer a specific professor)

The results will show you:
- Course name and section
- Meeting days and times
- Available seats
- Instructor name
- Room location

Remember that some courses fill up quickly, so I recommend registering as soon as your registration period opens. Would you like advice on specific courses?""",
            "no_response": """Alright! If you ever need help with course selection or have questions about specific courses, feel free to ask. 

Is there anything else I can help you with regarding your studies at North American University?"""
        }
    },
    "how do i access my nau portal": {
        "answer": """Here are the steps to access the North American University (NAU) student portal:
1. Open the school website : https://www.na.edu/
2. Click on the NAU Portal on the top menu
3. Enter your username and password
Let me know if you have any other questions about accessing your NAU student portal!""",
        "sources": ["https://www.na.edu/it-services/"],
        "follow_up": {
            "question": "Are you having trouble logging in to your portal?",
            "yes_response": """If you're having trouble logging in, here are some troubleshooting steps:

1. Make sure you're using the correct username format (usually firstname.lastname or first initial followed by lastname)
2. Check that Caps Lock is not enabled when typing your password
3. Clear your browser cache and cookies, then try again
4. Try using a different browser (Chrome, Firefox, Edge)
5. If you've forgotten your password, follow the "Forgot Password" link on the login page

If none of these steps work, you can contact the IT Help Desk:
- Email: support@na.edu
- Phone: 832-230-5541
- Hours: Monday-Friday, 8:00 AM - 5:00 PM

Would you like me to explain any of these steps in more detail?""",
            "no_response": """Great! If you ever encounter any issues with the portal, don't hesitate to ask for help. 

The portal is where you'll find important information like:
- Course registration
- Grades and academic records
- Financial information
- Campus announcements
- Access to university email

Is there anything specific you're looking to do in the portal?"""
        }
    }
}

# Exact match patterns for the predefined questions
EXACT_MATCHES = {
    "what are the tuition fees": ["what are the tuition fees", "tuition fees", "what are the tuition and fees", "how much is tuition"],
    "how do i apply for admission": ["how do i apply for admission", "how do i apply", "application process", "how to apply"],
    "what programs does nau offer": ["what programs does nau offer", "programs offered", "available degrees", "majors", "degree programs"],
    "how to reset my password": ["how to reset my password", "reset password", "forgot password", "change password"],
    "how do i select the courses": ["how do i select the courses", "select courses", "register for classes", "course registration"],
    "how do i access my nau portal": ["how do i access my nau portal", "access portal", "login to portal", "student portal"]
}

# Create a minimal knowledge base as fallback
def create_minimal_knowledge_base():
    knowledge = [
        {
            "content": "North American University (NAU) is a private, non-profit university located in Stafford, Texas. NAU offers undergraduate and graduate programs in Business Administration, Computer Science, and Education.",
            "source": "https://www.na.edu/about/",
            "title": "About NAU"
        },
        {
            "content": "Tuition for international undergraduate students at North American University is as follows: 1 to 11 credits: $1,125 per credit; 12 to 16 credits per academic semester: $13,500; Each additional credit over 16 credits: $1,125 per credit; Summer tuition (per class): $873.",
            "source": "https://www.na.edu/admissions/tuition-and-fees/",
            "title": "Tuition and Fees"
        },
        {
            "content": "Housing options at NAU include: Housing On Campus 2 Bed-Room only for men: $2,500.00 per semester, Housing On Campus 3 Bed-Room only for men: $2,100.00 per semester, Housing On Campus 4 Bed-Room only for men: $1,900.00 per semester, Housing on Hotel 2 Bed-Room: $3,600.00 per semester, Housing on Hotel 3 Bedroom: $3,000.00 per semester, Housing on Apartment 2 Bedroom: $3,200.00 per semester, Summer Housing: $1,250.00.",
            "source": "https://www.na.edu/campus-life/housing/",
            "title": "Housing Options"
        },
        {
            "content": "Meal service options at NAU include: 19-Meal per Week: $2,500.00 per semester, 14-Meal per Week: $1,900.00 per semester, 10-Meal per Week: $1,300.00 per semester.",
            "source": "https://www.na.edu/campus-life/dining-services/",
            "title": "Dining Services"
        },
        {
            "content": "North American University offers scholarships and financial aid to qualified students. These include merit-based scholarships, need-based grants, and work-study opportunities. International students may be eligible for certain scholarships as well.",
            "source": "https://www.na.edu/admissions/financial-aid/",
            "title": "Financial Aid"
        },
        {
            "content": "To apply to North American University, students need to submit an application form, official transcripts, and proof of English proficiency (for international students). Application deadlines vary by semester.",
            "source": "https://www.na.edu/admissions/",
            "title": "Admissions"
        }
    ]
    return knowledge

def clean_response_format(text):
    """
    Clean up response text to remove markdown formatting and special characters.
    """
    # Remove bold/italic formatting
    cleaned_text = re.sub(r'\*\*|\*', '', text)
    
    # Replace markdown links [text](url) with just the text
    cleaned_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned_text)
    
    # Remove markdown headers
    cleaned_text = re.sub(r'#{1,6}\s+', '', cleaned_text)
    
    # Replace emoji
    cleaned_text = re.sub(r'🎓|👨‍🎓|👩‍🎓|📚|📝|🏫|🎉|🎊|🎯|✅|✓|☑|✔', '', cleaned_text)
    
    # Fix any excessive spaces created by the replacements
    cleaned_text = re.sub(r' +', ' ', cleaned_text)
    cleaned_text = re.sub(r'\n +', '\n', cleaned_text)
    
    return cleaned_text

# Function to find a predefined answer for a query - now using exact matches
def get_predefined_answer(query):
    # Clean and normalize the query
    clean_query = re.sub(r'[^\w\s]', '', query.lower().strip())
    
    # Check for exact matches against our predefined patterns
    for key, patterns in EXACT_MATCHES.items():
        for pattern in patterns:
            # Check for exact match or if the query contains the pattern exactly as a phrase
            if clean_query == pattern or pattern in clean_query:
                logger.info(f"Found predefined answer for '{pattern}'")
                return predefined_answers[key]
    
    # Check for password reset related queries with special priority
    if any(word in clean_query for word in ["password", "reset", "forgot", "change password", "cant login"]):
        logger.info("Found password reset related query")
        return predefined_answers["how to reset my password"]
    
    # No exact match found
    return None

# Process a response based on a follow-up answer
def process_follow_up_response(follow_up, user_response):
    user_response = user_response.lower().strip()
    
    # Check if this is a yes/no question
    if "yes_response" in follow_up and "no_response" in follow_up:
        if any(word in user_response for word in ["yes", "yeah", "yep", "sure", "definitely", "absolutely"]):
            logger.info("Responding with 'yes' response to follow-up")
            return follow_up["yes_response"]
        elif any(word in user_response for word in ["no", "nope", "not", "don't", "dont"]):
            logger.info("Responding with 'no' response to follow-up")
            return follow_up["no_response"]
    
    # Check if this is an undergraduate/graduate question
    elif "undergraduate_response" in follow_up and "graduate_response" in follow_up:
        if any(word in user_response for word in ["undergraduate", "bachelor", "bachelors", "bs", "ba"]):
            logger.info("Responding with undergraduate information")
            return follow_up["undergraduate_response"]
        elif any(word in user_response for word in ["graduate", "master", "masters", "mba", "ms", "phd"]):
            logger.info("Responding with graduate information")
            return follow_up["graduate_response"]
    
    # For custom responses that require more specific handling
    elif "custom_response" in follow_up and follow_up["custom_response"]:
        logger.info("Processing custom response for program information")
        # For the "Which program are you most interested in?" question
        programs = {
            "business": "The Bachelor of Business Administration (BBA) program at NAU offers concentrations in Accounting, Finance, International Business, and Management. Students learn key business principles and develop leadership skills. The BBA requires 120 credit hours including general education courses, business core courses, and concentration courses.",
            "computer science": "The Computer Science program at NAU offers a comprehensive curriculum covering programming, algorithms, database management, and software engineering. Students can specialize in areas like AI, cybersecurity, or data science. The program prepares graduates for careers as software developers, systems analysts, and IT consultants.",
            "education": "The Education program at NAU prepares students for careers in teaching and educational administration. The program offers specializations in Early Childhood Education, Bilingual Education, and Educational Leadership. Students complete coursework and supervised teaching experiences to prepare for teacher certification.",
            "criminal justice": "The Criminal Justice program at NAU covers law enforcement, corrections, and legal systems. Students learn about criminal behavior, constitutional law, and public policy. The program prepares graduates for careers in law enforcement, corrections, homeland security, and legal services."
        }
        
        for prog_key, prog_desc in programs.items():
            if prog_key in user_response:
                logger.info(f"Providing information about the {prog_key} program")
                return prog_desc
        
        # If no specific program matched, give a general response
        logger.info("No specific program matched, giving general response")
        return "Each program at NAU is designed to provide a strong educational foundation and practical skills. I'd be happy to provide more specific information about any program that interests you. Just let me know which one you'd like to learn more about."
    
    # Default general response if we can't determine what the user meant
    logger.info("Using default follow-up response")
    return "I'm sorry, I'm not sure how to help with that specific request. Is there something else about North American University that I can assist you with?"

# Function to use OpenAI's web search API
async def search_web_with_openai(query):
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Use the appropriate web search model
        logger.info("Using OpenAI web search...")
        
        # Location info for a U.S. based query - adjust if needed
        user_location = {
            "type": "approximate",
            "approximate": {
                "country": "US",
                "city": "Stafford",
                "region": "Texas"
            }
        }
        
        # Make request with proper web_search_options
        response = client.chat.completions.create(
            model="gpt-4o-search-preview",  # Must use a -search- model variant
            web_search_options={
                "search_context_size": "medium",  # Balance between quality and speed
                "user_location": user_location    # Location to improve relevance
            },
            messages=[
                {
                    "role": "system", 
                    "content": """You are the official AI chatbot for North American University (NAU). Your primary purpose is to provide students with accurate, helpful information about NAU programs, services, and policies.

Use search results to provide detailed, accurate information about North American University. 
Focus on the official NA.edu website content when available. If information isn't available from search, clearly state that and suggest contacting the appropriate department.

STRICT FORMATTING REQUIREMENTS (MUST FOLLOW):
1. NEVER use asterisks (*) for any purpose - not for emphasis, not for bullets
2. NEVER use hash/pound signs (#) for any purpose
3. NEVER include URLs in your main text
4. Use ONLY plain text formatting
5. For lists, use ONLY plain dashes (-) at the start of lines
6. DO NOT use markdown formatting of any kind
7. DO NOT use emojis or special characters
8. IF you need to mention a website name, use plain text only

DEPARTMENT CONTACT INFORMATION:
- IT/Technical issues: support@na.edu or 832-230-5541 (never mention helpdesk@na.edu)
- Facilities/Housing/Meal plans: housing@na.edu
- Admissions: admissions@na.edu
- Financial aid: finaid@na.edu
- Academic advising: advising@na.edu
- International student services: international@na.edu

FORMAT:
- Use a warm, conversational tone (e.g., "I'd be happy to help with that!")
- Format numerical information with bullet points using hyphens (-)
- Start responses with "I can help with that..." or similar friendly opener
- End responses with an offer to help with other questions

Use a warm, conversational tone and format information with bullet points where appropriate.
End responses with an offer to help with other questions."""
                },
                {
                    "role": "user",
                    "content": f"Question about North American University: {query}"
                }
            ]
        )
        
        # Extract the assistant's response
        answer = response.choices[0].message.content
        
        # Extract citations if available
        sources = []
        if hasattr(response.choices[0].message, 'annotations'):
            for annotation in response.choices[0].message.annotations:
                if hasattr(annotation, 'type') and annotation.type == 'url_citation':
                    if hasattr(annotation, 'url_citation') and hasattr(annotation.url_citation, 'url'):
                        sources.append(annotation.url_citation.url)
        
        # Fallback to na.edu if no sources found
        if not sources:
            sources = ["https://www.na.edu"]
        
        logger.info(f"Successfully received web search response with {len(sources)} sources")
        
        return {
            "answer": answer,
            "sources": sources
        }
    
    except Exception as e:
        logger.error(f"Error with web search: {str(e)}")
        # Fallback response in case of error
        return {
            "answer": f"I apologize, but I'm having trouble searching for information about that. Please try asking in a different way or contact NAU directly for assistance.",
            "sources": ["https://www.na.edu"]
        }

# Fallback function when web search fails
async def fallback_response(query):
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Use system prompt from the original code
        system_prompt = """You are the official AI chatbot for North American University (NAU). Your primary purpose is to provide students with accurate, helpful information about NAU programs, services, and policies.

RESPONSE PRIORITIES:
1. PREDEFINED ANSWERS: For common questions about tuition, admissions, programs, password resets, course selection, and portal access, provide the complete predefined answer with all details.
2. DEPARTMENT REDIRECTION: If the information isn't readily available, direct students to the appropriate department.

STRICT FORMATTING REQUIREMENTS (MUST FOLLOW):
1. NEVER use asterisks (*) for any purpose - not for emphasis, not for bullets
2. NEVER use hash/pound signs (#) for any purpose
3. NEVER include URLs in your main text
4. Use ONLY plain text formatting
5. For lists, use ONLY plain dashes (-) at the start of lines
6. DO NOT use markdown formatting of any kind
7. DO NOT use emojis or special characters
8. IF you need to mention a website name, use plain text only

DEPARTMENT CONTACT INFORMATION:
- IT/Technical issues: support@na.edu or 832-230-5541 (never mention helpdesk@na.edu)
- Facilities/Housing/Meal plans: housing@na.edu
- Admissions: admissions@na.edu
- Financial aid: finaid@na.edu
- Academic advising: registrar@na.edu
- International student services: international@na.edu

RESPONSE STYLE:
- Use a warm, conversational tone 
- Format numerical information with simple dashes (-)
- Start responses with "I can help with that..." or similar friendly opener
- End responses with an offer to help with other questions

CONTENT RESTRICTIONS:
- Only provide information related to North American University
- Never mention training data or your training process
- For non-NAU questions, politely redirect: "I can only assist with topics related to North American University."
- Only provide answers from www.na.edu website, not from the other websites."""
        
        context = json.dumps(create_minimal_knowledge_base())
        
        # Try to use web search with a different approach
        try:
            # Use web search with minimal options
            response = client.chat.completions.create(
                model="gpt-4o-search-preview",  # Using the search-capable model
                web_search_options={},  # Minimal web search options
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Please find information about North American University regarding this question: {query}"}
                ],
                temperature=0
            )
            
            answer = response.choices[0].message.content
            logger.info("Successfully received response from backup web search")
            
            # Extract any available sources
            sources = []
            if hasattr(response.choices[0].message, 'annotations'):
                for annotation in response.choices[0].message.annotations:
                    if hasattr(annotation, 'type') and annotation.type == 'url_citation':
                        if hasattr(annotation, 'url_citation') and hasattr(annotation.url_citation, 'url'):
                            sources.append(annotation.url_citation.url)
            
            # Use default source if none found
            if not sources:
                sources = ["https://www.na.edu"]
                
            return {
                "answer": answer,
                "sources": sources
            }
            
        except Exception as web_search_error:
            logger.error(f"Backup web search failed: {str(web_search_error)}")
            
            # Final fallback to standard model with our knowledge base
            response = client.chat.completions.create(
                model="gpt-4o",  # Standard model as last resort
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context about North American University: {context}\n\nUser Question: {query}"}
                ],
                temperature=0
            )
            
            answer = response.choices[0].message.content
            logger.info("Successfully received response from standard OpenAI API")
            return {
                "answer": answer,
                "sources": ["https://www.na.edu"]
            }
            
    except Exception as fallback_error:
        logger.error(f"Fallback API error: {str(fallback_error)}")
        return {
            "answer": "I apologize, but I'm having trouble processing your request at the moment. Please try again later or contact NAU directly for assistance.",
            "sources": ["https://www.na.edu"]
        }

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

@app.route('/api/chat', methods=['POST'])
async def chat():
    try:
        data = request.json
        query = data.get('query', '')
        follow_up_to = data.get('follow_up_to', None)
        original_question = data.get('original_question', '')
        
        logger.info(f"Received chat request - query: {query}, follow_up_to: {follow_up_to}")
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
            
        # If this is a follow-up response
        if follow_up_to and original_question:
            logger.info(f"Processing follow-up response to: {follow_up_to}")
            
            predefined = get_predefined_answer(original_question)
            if predefined and "follow_up" in predefined:
                answer = process_follow_up_response(predefined["follow_up"], query)
                sources = predefined.get("sources", ["https://www.na.edu"])

                # Clean answer
                answer = clean_response_format(answer)

                return jsonify({
                    "answer": answer,
                    "sources": sources
                })
        
        # Check for predefined answers first
        predefined = get_predefined_answer(query)
        if predefined:
            answer = predefined["answer"]
            sources = predefined["sources"]

            # Clean answer
            answer = clean_response_format(answer)

            logger.info("Using predefined answer")
            response_data = {
                "answer": answer,
                "sources": sources
            }

            if "follow_up" in predefined:
                follow_up = predefined["follow_up"]["question"]
                follow_up_id = f"followup_{int(time.time())}"
                response_data["follow_up"] = follow_up
                response_data["follow_up_id"] = follow_up_id
                response_data["original_question"] = query

            return jsonify(response_data)
        
        else:
            # No predefined answer, use OpenAI web search
            logger.info("No predefined answer found, using web search...")
            
            try:
                search_result = await search_web_with_openai(query)
                answer = search_result["answer"]
                sources = search_result["sources"]

                # Clean answer
                answer = clean_response_format(answer)

                return jsonify({
                    "answer": answer,
                    "sources": sources
                })
            except Exception as api_error:
                logger.error(f"Web search API error: {str(api_error)}")

                try:
                    fallback_result = await fallback_response(query)
                    answer = fallback_result["answer"]
                    sources = fallback_result["sources"]

                    # Clean answer
                    answer = clean_response_format(answer)

                    return jsonify({
                        "answer": answer,
                        "sources": sources
                    })
                except Exception as fallback_error:
                    logger.error(f"Fallback API error: {str(fallback_error)}")
                    error_answer = "I apologize, but I'm having trouble processing your request at the moment. Please try again later or contact NAU directly for assistance."
                    
                    return jsonify({
                        "answer": error_answer,
                        "sources": ["https://www.na.edu"]
                    })
    
    except Exception as e:
        import traceback
        logger.error(f"Error processing query: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Server error: {str(e)}"}), 500


if __name__ == '__main__':
    logger.info("Starting North American University AI Assistant with Web Search (No Chat Storage)")
    # Use Hypercorn ASGI server which supports async
    import hypercorn.asyncio
    import hypercorn.config
    
    config = hypercorn.config.Config()
    config.bind = ["127.0.0.1:5000"]
    config.use_reloader = True
    
    asyncio.run(hypercorn.asyncio.serve(app, config))