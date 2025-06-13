import os
import json
import re
import openai
import streamlit as st
from PyPDF2 import PdfReader
import uuid
import plotly.graph_objects as go  

def clean_json_response(response_text: str) -> str:
    cleaned = re.sub(r"^```(?:json)?\s*", "", response_text)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()

class ATSEvaluator:
    def __init__(self):
        self.initialize_session()
        self.load_openai_api_key()

    def initialize_session(self):
        """Initialize session state for ATS evaluation."""
        if 'session_id' not in st.session_state:
            st.session_state['session_id'] = str(uuid.uuid4())
        if 'ats_report' not in st.session_state:
            st.session_state['ats_report'] = None
        if 'pdf_text' not in st.session_state:
            st.session_state['pdf_text'] = ""
        if 'uploaded_file_name' not in st.session_state:
            st.session_state['uploaded_file_name'] = None

    def load_openai_api_key(self):
        """Load OpenAI API key from Streamlit Secrets or Environment Variables."""
        try:
            self.OPENAI_API_KEY = st.secrets["openai"]["api_key"]
        except KeyError:
            self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

        if not self.OPENAI_API_KEY:
            st.error("OpenAI API key not found! Please set it in Streamlit Secrets or as an environment variable.")
            st.stop()
        else:
            openai.api_key = self.OPENAI_API_KEY

    def extract_text_from_pdf(self, uploaded_file):
        """Extract text from a PDF file."""
        reader = PdfReader(uploaded_file)
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        return text

    def call_openai(self, prompt):
        """Call OpenAI API to get ATS evaluation."""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert in evaluating CVs/Resumes for Applicant Tracking Systems (ATS). "
                            "When given the text of a CV/Resume, return an evaluation in JSON format with the following keys: "
                            "'overall_score' (0-100), "
                            "'formatting_score' (0-100), "
                            "'keyword_score' (0-100), "
                            "'keyword_match' (0-100) indicating how many important job-related keywords match, "
                            "'skills_check' (0-100) indicating if the CV has the required skills, "
                            "'experience_check' (0-100) indicating if the work experience is relevant, "
                            "'grammar_check' (0-100) indicating spelling and grammar accuracy, "
                            "'contact_info_check' (0-100) indicating whether contact information is correctly provided, "
                            "'file_check' (0-100) indicating if the PDF is ATS-readable, "
                            "'job_title_match' (0-100) indicating if job titles match industry standards, "
                            "'education_check' (0-100) evaluating the quality or relevance of the education section, "
                            "'certification_check' (0-100) evaluating the presence and relevance of certifications, "
                            "'professional_summary_check' (0-100) evaluating the quality of the professional summary, "
                            "'customization_check' (0-100) evaluating if the CV is tailored for the job, "
                            "'consistency_check' (0-100) evaluating consistency in formatting and style, "
                            "'visual_consistency_check' (0-100) evaluating the visual layout and consistency, "
                            "'action_oriented_language_check' (0-100) evaluating if the language is action-oriented, "
                            "'file_metadata_check' (0-100) evaluating if file metadata is optimized for ATS, "
                            "and 'recommendations' (a list of 3 specific suggestions for improvement). "
                            "Ensure that the output is valid JSON."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            return response['choices'][0]['message']['content'].strip()
        except Exception as e:
            return f"Error calling OpenAI API: {str(e)}"

    def run(self):
        uploaded_file = st.file_uploader("Upload a CV or Resume (PDF)", type=["pdf"])

        if uploaded_file is not None:
            if st.session_state.get('uploaded_file_name') != uploaded_file.name:
                st.session_state['ats_report'] = None
                st.session_state['pdf_text'] = ""
                st.session_state['uploaded_file_name'] = uploaded_file.name
                with st.spinner("Extracting text from CV/Resume..."):
                    pdf_text = self.extract_text_from_pdf(uploaded_file)
                    st.session_state['pdf_text'] = pdf_text

            if st.button("Generate ATS Evaluation"):
                with st.spinner("Evaluating CV for ATS compatibility..."):
                    prompt = (
                        "Please evaluate the following CV/Resume for ATS compatibility. Provide scores (all out of 100) for the following: \n"
                        "- Overall ATS Score\n"
                        "- Formatting Score (ATS-friendly layout)\n"
                        "- Keyword Score (overall keyword optimization)\n"
                        "- Keyword Match (number of important job-related keywords that match)\n"
                        "- Skills Check (presence of required skills)\n"
                        "- Experience Check (relevance of work experience)\n"
                        "- Grammar Check (spelling and grammar accuracy)\n"
                        "- Contact Info Check (correct contact information)\n"
                        "- File Check (PDF readability by ATS)\n"
                        "- Job Title Match (job titles matching industry standards)\n"
                        "- Education Check (quality and relevance of education details)\n"
                        "- Certification Check (presence and relevance of certifications)\n"
                        "- Professional Summary Check (quality of the professional summary)\n"
                        "- Customization Check (tailoring of the CV for the job)\n"
                        "- Consistency Check (consistency in formatting and style)\n"
                        "- Visual Consistency Check (visual layout and consistency)\n"
                        "- Action-Oriented Language Check (use of action verbs and language)\n"
                        "- File Metadata Check (optimization of file metadata for ATS)\n"
                        "Also, include 3 actionable recommendations for improvement. "
                        "Return your answer as a valid JSON object with keys: "
                        "'overall_score', 'formatting_score', 'keyword_score', 'keyword_match', 'skills_check', 'experience_check', "
                        "'grammar_check', 'contact_info_check', 'file_check', 'job_title_match', 'education_check', 'certification_check', "
                        "'professional_summary_check', 'customization_check', 'consistency_check', 'visual_consistency_check', "
                        "'action_oriented_language_check', 'file_metadata_check', and 'recommendations'.\n\n"
                        f"CV/Resume Content:\n{st.session_state['pdf_text'][:5000]}"
                    )
                    response_text = self.call_openai(prompt)
                    response_text = clean_json_response(response_text)
                    try:
                        ats_report = json.loads(response_text)
                        st.session_state['ats_report'] = ats_report
                    except Exception as e:
                        st.error("Failed to parse evaluation report. Please try again.")
                        st.write("Response from API:", response_text)

        if st.session_state.get('ats_report'):
            report = st.session_state['ats_report']
            st.subheader("ATS Evaluation Report")

            thresholds = {
                "overall_score": 70,
                "formatting_score": 70,
                "keyword_score": 70,
                "keyword_match": 70,
                "skills_check": 70,
                "experience_check": 70,
                "grammar_check": 70,
                "contact_info_check": 80,
                "file_check": 70,
                "job_title_match": 70,
                "education_check": 70,
                "certification_check": 70,
                "professional_summary_check": 70,
                "customization_check": 70,
                "consistency_check": 70,
                "visual_consistency_check": 70,
                "action_oriented_language_check": 70,
                "file_metadata_check": 70
            }

            metrics = [
                ("Overall ATS Score", "overall_score"),
                ("Formatting Score", "formatting_score"),
                ("Keyword Score", "keyword_score"),
                ("Keyword Match", "keyword_match"),
                ("Skills Check", "skills_check"),
                ("Experience Check", "experience_check"),
                ("Grammar Check", "grammar_check"),
                ("Contact Info Check", "contact_info_check"),
                ("File Check", "file_check"),
                ("Job Title Match", "job_title_match"),
                ("Education Check", "education_check"),
                ("Certification Check", "certification_check"),
                ("Professional Summary Check", "professional_summary_check"),
                ("Customization Check", "customization_check"),
                ("Consistency Check", "consistency_check"),
                ("Visual Consistency Check", "visual_consistency_check"),
                ("Action-Oriented Language Check", "action_oriented_language_check"),
                ("File Metadata Check", "file_metadata_check")
            ]

            with st.expander("Metrics"):
                st.markdown("### Metrics")
                for i in range(0, len(metrics), 3):
                    cols = st.columns(3)
                    for j, col in enumerate(cols):
                        if i + j < len(metrics):
                            display_name, key = metrics[i + j]
                            score = report.get(key, "N/A")
                            if isinstance(score, (int, float)):
                                threshold = thresholds.get(key, 70)
                                delta_value = score - threshold
                                delta_str = f"{delta_value:+}"
                                col.metric(display_name, score, delta=delta_str, delta_color="normal")
                            else:
                                col.metric(display_name, score)

            with st.expander("Visualizations"):
                st.markdown("### Visualizations")
                for i in range(0, len(metrics), 4):
                    cols = st.columns(4)
                    for j, col in enumerate(cols):
                        if i + j < len(metrics):
                            display_name, key = metrics[i + j]
                            score = report.get(key, "N/A")
                            if isinstance(score, (int, float)):
                                threshold = thresholds.get(key, 70)
                                fig = go.Figure(go.Indicator(
                                    mode="gauge+number",
                                    value=score,
                                    gauge={
                                        'axis': {'range': [0, 100]},
                                        'bar': {'color': "green" if score >= threshold else "red"},
                                        'steps': [
                                            {'range': [0, threshold], 'color': "red"},
                                            {'range': [threshold, 100], 'color': "green"}
                                        ]
                                    },
                                    title={"text": display_name}
                                ))
                                col.plotly_chart(fig, use_container_width=True)

            with st.expander("Recommendations for Improvement"):
                st.markdown("### Recommendations for Improvement:")
                recommendations = report.get("recommendations", [])
                if isinstance(recommendations, list):
                    for rec in recommendations:
                        st.write(f"- {rec}")
                else:
                    st.write(recommendations)

if __name__ == "__main__":
    st.set_page_config(page_title="ATS Evaluation")
    evaluator = ATSEvaluator()
    evaluator.run()
