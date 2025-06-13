import streamlit as st
from datetime import datetime
import json
import psycopg2
from db import Database
from ats_evaluation import ATSEvaluator

class CVService:
    def __init__(self, db: Database):
        self.db = db
        self._create_table()

    def _create_table(self):
        """Create the user_cvs table if it does not exist."""
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS user_cvs (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER,
                        file_name TEXT,
                        ats_score FLOAT,
                        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        cv_data BYTEA
                    );
                ''')
            conn.commit()

    def add_cv(self, user_id, file_name, ats_score, cv_data):
        """Insert a new CV record and return its ID."""
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    INSERT INTO user_cvs (user_id, file_name, ats_score, cv_data)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                    ''',
                    (user_id, file_name, ats_score, psycopg2.Binary(cv_data))
                )
                cv_id = cur.fetchone()[0]
            conn.commit()
        return cv_id

    def get_cvs(self, user_id):
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT id, file_name, ats_score, upload_date
                    FROM user_cvs
                    WHERE user_id = %s
                    ORDER BY upload_date DESC;
                    ''',
                    (user_id,)
                )
                return cur.fetchall()

    def get_cv_data(self, cv_id):
        """Retrieve the stored binary data of a CV by its ID."""
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT cv_data FROM user_cvs
                    WHERE id = %s;
                    ''',
                    (cv_id,)
                )
                result = cur.fetchone()
                if result:
                    cv_data = result[0]
                    if isinstance(cv_data, memoryview):
                        cv_data = cv_data.tobytes()
                    return cv_data
                return None

    def delete_cv(self, cv_id):
        """Delete a CV record by its ID."""
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM user_cvs WHERE id = %s", (cv_id,))
            conn.commit()

def run_cv_upload():
    user = st.session_state.get("user")
    if not user:
        st.error("You must be logged in to upload CVs.")
        st.stop()

    user_id = user.get("id")
    db = Database()
    cv_service = CVService(db)
    ats_evaluator = ATSEvaluator()

    st.write("#### Upload Your CV")
    with st.form("cv_upload_form", clear_on_submit=True):
        uploaded_file = st.file_uploader("Select a PDF file", type=["pdf"])
        st.info("Upload your CV (PDF only) to receive an ATS evaluation. Your CV must score at least 70 overall to be accepted.")
        submit_button = st.form_submit_button("Upload CV")

    if submit_button:
        if not uploaded_file:
            st.error("Please select a file to upload.")
        else:
            st.info("Evaluating your CV, please wait...")
            pdf_text = ats_evaluator.extract_text_from_pdf(uploaded_file)
            prompt = (
                "Please evaluate the following CV/Resume for ATS compatibility. "
                "Return a JSON response with at least an 'overall_score' key.\n\n"
                f"CV Content:\n{pdf_text[:5000]}"
            )
            response_text = ats_evaluator.call_openai(prompt).strip()

            try:
                ats_report = json.loads(response_text)
                overall_score = ats_report.get("overall_score")
            except Exception as e:
                st.error("Failed to parse ATS evaluation. Please try again.")
                st.write("Response from API:", response_text)
                overall_score = None

            if overall_score is None:
                st.error("Could not determine an ATS score.")
            else:
                st.write(f"**ATS Overall Score:** {overall_score}")
                if overall_score < 70:
                    st.error("Your CV ATS score is below 70. Please improve your CV and try again.")
                else:
                    uploaded_file.seek(0)
                    cv_data = uploaded_file.read()
                    file_name = uploaded_file.name
                    cv_id = cv_service.add_cv(user_id, file_name, overall_score, cv_data)
                    st.success("Your CV has been uploaded successfully!")

    st.write("#### Filter Uploaded CVs")
    st.markdown("Use the filters below to search for your uploaded CVs.")
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        search_term = st.text_input("Search by File Name", placeholder="Enter part of the file name...")
    with filter_col2:
        min_score = st.number_input("Minimum ATS Score", min_value=0, max_value=100, value=0, step=1)
    with filter_col3:
        max_score = st.number_input("Maximum ATS Score", min_value=0, max_value=100, value=100, step=1)

    st.write("#### Your Uploaded CVs")
    st.markdown(
        """
        <style>
        .st-emotion-cache-ue6h4q {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    cvs = cv_service.get_cvs(user_id)
    if cvs:
        filtered_cvs = []
        for cv in cvs:
            cv_id, file_name, ats_score, upload_date = cv
            if search_term.lower() in file_name.lower() and min_score <= ats_score <= max_score:
                filtered_cvs.append(cv)

        if filtered_cvs:
            col1, col2, col3, col4 = st.columns([0.45, 0.2, 0.2, 0.15])
            with col1:
                st.write("##### File Name")
            with col2:
                st.write("##### ATS Score")
            with col3:
                st.write("##### Uploaded On")
            with col4:
                st.write("##### Actions")
            st.write("---")

            for cv in filtered_cvs:
                cv_id, file_name, ats_score, upload_date = cv
                col1, col2, col3, col4 = st.columns([0.45, 0.2, 0.2, 0.15])
                with col1:
                    st.write(file_name)
                with col2:
                    st.write(ats_score)
                with col3:
                    try:
                        upload_dt = upload_date if isinstance(upload_date, datetime) \
                            else datetime.strptime(upload_date, "%Y-%m-%d %H:%M:%S")
                        st.write(upload_dt.strftime("%Y-%m-%d %H:%M:%S"))
                    except Exception:
                        st.write("N/A")
                with col4:
                    action = st.selectbox("Actions", ["Select", "Download", "Delete"], key=f"action_{cv_id}")
                    if action == "Download":
                        cv_data = cv_service.get_cv_data(cv_id)
                        if cv_data:
                            st.download_button("Click to Download", data=cv_data, file_name=file_name, mime="application/pdf", key=f"download_{cv_id}")
                    elif action == "Delete":
                        cv_service.delete_cv(cv_id)
                        st.success("CV deleted successfully!")
                        st.rerun()
        else:
            st.info("No CVs match your filter criteria.")
    else:
        st.info("You have not uploaded any CVs yet.")

if __name__ == "__main__":
    st.set_page_config(page_title="CV Upload", layout="wide")
    run_cv_upload()
