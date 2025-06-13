from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pdf_utils import pdf_to_text 

def match_resumes(job_description, resumes):
    vectorizer = TfidfVectorizer()
    job_vector = vectorizer.fit_transform([job_description])
    resume_texts = [pdf_to_text(resume[3]) for resume in resumes]  
    resume_vectors = vectorizer.transform(resume_texts)
    similarities = cosine_similarity(job_vector, resume_vectors)
    return similarities[0]
