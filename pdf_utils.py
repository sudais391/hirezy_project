import PyPDF2
import io

def pdf_to_text(pdf_data):
    reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text
