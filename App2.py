from flask import Flask, render_template, request, jsonify, redirect, flash
from werkzeug.utils import secure_filename
import os
import re
import spacy
import fitz  # PyMuPDF for PDF parsing
from docx import Document
import pytesseract
from PIL import Image
import io
from spacy.matcher import Matcher

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'jpg', 'jpeg', 'png'}

# Ensure the 'uploads' directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_pdf(pdf_path):
    """Preprocess PDF by removing headers and footers."""
    try:
        pdf_document = fitz.open(pdf_path)
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            header_region = fitz.Rect(0, 0, page.rect.width, 50)
            page.draw_rect(header_region, fill=(1, 1, 1))
            footer_region = fitz.Rect(0, page.rect.height - 50, page.rect.width, page.rect.height)
            page.draw_rect(footer_region, fill=(1, 1, 1))
        preprocessed_path = os.path.join(UPLOAD_FOLDER, 'preprocessed.pdf')
        pdf_document.save(preprocessed_path)
        pdf_document.close()
        return preprocessed_path
    except Exception as e:
        print(f"Error preprocessing PDF: {e}")
        return None

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF, handling OCR for scanned PDFs."""
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                if page.get_text():
                    text += page.get_text()
                else:
                    images = page.get_images(full=True)
                    for img_index, img in enumerate(images):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image = Image.open(io.BytesIO(image_bytes))
                        text += pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def extract_text_from_docx(docx_path):
    """Extract text from DOCX."""
    try:
        doc = Document(docx_path)
        full_text = [para.text for para in doc.paragraphs]
        return '\n'.join(full_text)
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return ""

def extract_text_from_image(image_path):
    """Extract text from image using OCR."""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Error extracting text from image: {e}")
        return ""

def extract_contact_number_from_resume(text):
    pattern = r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
    match = re.search(pattern, text)
    return match.group() if match else None

def extract_email_from_resume(text):
    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    match = re.search(pattern, text)
    return match.group() if match else None

def extract_skills_from_resume(text):
    unique_skills = set()
    skills_list = [
    "Python", "Java", "C++", "Machine Learning", "Data Analysis", 
    "Project Management", "JavaScript", "HTML", "CSS", "SQL", "R", 
    "Statistical Analysis", "Artificial Intelligence", "Deep Learning", 
    "Natural Language Processing", "Computer Vision", "Problem Solving", 
    "Communication Skills", "Teamwork", "Time Management",
    "Leadership", "Critical Thinking", "Data Visualization", "Big Data",
    "Database Management", "Software Development", "Agile Methodologies",
    "Scrum", "Git", "Docker", "Kubernetes", "Cloud Computing", "AWS", 
    "Azure", "Google Cloud Platform", "Data Mining", "ETL Processes", 
    "Business Intelligence", "Excel", "Power BI", "Tableau", "SAP", 
    "TensorFlow", "Keras", "PyTorch", "Hadoop", "Spark", "Linux", 
    "Unix", "NoSQL", "MongoDB", "Redis", "GraphQL", "REST APIs",
    "UI/UX Design", "User Research", "Product Management", "Innovation",
    "Cybersecurity", "Penetration Testing", "Encryption", "Network Security",
    "Blockchain", "Cryptocurrency", "Fintech", "IoT", "Augmented Reality",
    "Virtual Reality", "Game Development", "Mobile Development", "Android",
    "iOS", "React", "Vue.js", "Angular", "Bootstrap", "Django", 
    "Flask", "Spring Boot", "Hibernate", "Jenkins", "CI/CD", "Automation",
    "Robotics", "Embedded Systems", "Signal Processing", "Quantum Computing",
    "Bioinformatics", "Genomics", "Healthcare Analytics", "Financial Modeling",
    "Risk Management", "Salesforce", "Customer Relationship Management",
    "ERP Systems", "Marketing", "SEO", "Content Management", "Technical Writing",
    "Grant Writing", "Event Planning", "Public Speaking", "Conflict Resolution",
    "Negotiation", "Interpersonal Skills", "Mentoring", "Coaching", "Employee Training",
    "Instructional Design", "E-learning Development", "Curriculum Development", 
    "Sociology", "Psychology", "Anthropology", "Economics", "Political Science",
    "QlikView", "Qlik Sense", "Qlik NPrinting", "Qlik GeoAnalytics", "Qlik DataMarket",
    "Qlik Connectors", "Qlik Cloud", "Qlik Analytics Platform", "Qlik Associative Model",
    "Qlik Data Integration", "Qlik Reporting", "Qlik Scripting", "Qlik Extensions"]

    pattern = r"\b(?:{})\b".format("|".join(re.escape(skill) for skill in skills_list))
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    for match in matches:
        unique_skills.add(match.lower())
    return list(unique_skills)

def extract_education_from_resume(text):
    education_qualifications = [
        "Bachelor's Degree", "Master's Degree", "Doctorate", "PhD", 
        "Diploma", "Certification", "Year", "Grade", "Percentage", 
        "College", "college", "University", "university", "HSC", "SSC"
    ]
    lines = text.split("\n")
    education_data = []
    for line in lines:
        for qualification in education_qualifications:
            if qualification.lower() in line.lower():
                education_data.append(line.strip())
                break
    return education_data

def extract_work_experience(text):
    # Placeholder function; replace with actual implementation
    return []

def extract_name(resume_text):
    nlp = spacy.load("en_core_web_sm")
    matcher = Matcher(nlp.vocab)
    patterns = [
        [{"POS": "PROPN"}, {"POS": "PROPN"}],  # First name and Last name
        [{"POS": "PROPN"}, {"POS": "PROPN"}, {"POS": "PROPN"}],  # First name, Middle name, and Last name
        [{"POS": "PROPN"}, {"POS": "PROPN"}, {"POS": "PROPN"}, {"POS": "PROPN"}]  # First name, Middle name, Middle name, and Last name
    ]
    for pattern in patterns:
        matcher.add("NAME", patterns=[pattern])
    doc = nlp(resume_text)
    matches = matcher(doc)
    for match_id, start, end in matches:
        span = doc[start:end]
        return span.text
    return None

def extract_address_from_resume(text):
    city_pattern = r"[\s,]([A-Z][a-zA-Z\s]+),"
    pincode_pattern = r"\b\d{6}\b"
    address_pattern = r"(?<!\d)[\dA-Za-z\s,-]+\s(?=city|pincode|$)"

    city_match = re.search(city_pattern, text)
    pincode_match = re.search(pincode_pattern, text)
    address_match = re.search(address_pattern, text)

    city = city_match.group(1) if city_match else None
    pincode = pincode_match.group() if pincode_match else None
    address = address_match.group().strip() if address_match else None

    formatted_address = f"{city}, {pincode}, {address}" if city and pincode and address else None

    return {"city": city, "pincode": pincode, "address": formatted_address}

@app.route('/', methods=['GET', 'POST'])
def index():
    extracted_data = {}
    if request.method == 'POST':
        if 'resume' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['resume']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Extract text based on file extension
            file_ext = filename.rsplit('.', 1)[1].lower()
            if file_ext == 'pdf':
                preprocessed_path = preprocess_pdf(file_path)
                if preprocessed_path:
                    text = extract_text_from_pdf(preprocessed_path)
            elif file_ext == 'docx':
                text = extract_text_from_docx(file_path)
            elif file_ext in {'jpg', 'jpeg', 'png'}:
                text = extract_text_from_image(file_path)
            else:
                flash('Unsupported file format')
                return redirect(request.url)

            # Extracted data
            extracted_data['name'] = extract_name(text)
            extracted_data['contact_number'] = extract_contact_number_from_resume(text)
            extracted_data['email'] = extract_email_from_resume(text)
            extracted_data['skills'] = extract_skills_from_resume(text)
            extracted_data['education'] = extract_education_from_resume(text)
            extracted_data['work_experience'] = extract_work_experience(text)
            extracted_data['address'] = extract_address_from_resume(text)

    return render_template('Template/upload_resume2.html', extracted_data=extracted_data)

if __name__ == '__main__':
    app.run(debug=True)
