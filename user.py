import streamlit as st
from streamlit_option_menu import option_menu
from chatbot import Chatbot
from ats_evaluation import ATSEvaluator
from db import Database
from cv_upload import CVService
from ats import JobService, ResumeService
from datetime import datetime, date

import streamlit.components.v1 as components

@st.dialog("Job Description", width="large")
def show_jd_dialog(jd):
    st.write("**Job Description:**")
    st.write(jd.strip())

@st.dialog("Applied Job Details", width="large")
def view_applied_job_dialog(job_id, company, title, description, skills, posted_date, last_date_to_apply, resume_service, cv_service, user_id):
    st.subheader(f"Company: {company}")
    st.subheader(f"Job Title: {title}")
    st.write(f"**Job Description:** {description}")
    st.write(f"**Required Skills:** {skills}")
    st.write(f"**Date Posted:** {posted_date}")
    st.write(f"**Last Date to Apply:** {last_date_to_apply}")

    st.markdown("### **Application Details**")
    st.write("You have already applied for this job.")

    with st.spinner("Loading application details..."):
        resumes = resume_service.get_resumes_for_job(job_id)
        user_cvs = cv_service.get_cvs(user_id)
        user_resume = next((r for r in resumes if r[3] in [cv[0] for cv in user_cvs]), None)  
        if user_resume:
            cv_name = next((cv[1] for cv in user_cvs if cv[0] == user_resume[3]), "Unknown CV")
            st.write(f"**Applied with CV:** {cv_name}")
            st.write(f"**Candidate Name:** {user_resume[2]}") 
        else:
            st.write("CV details not found.")

    st.write("Your application details are stored, and you cannot apply for the same job again.")

@st.dialog("Job Application", width="large")
def apply_for_job(job_id, title, company, description, skills, posted_date, last_date_to_apply, cv_service, user_id, resume_service, db):
    st.subheader(f"Company: {company}")
    st.subheader(f"Job Title: {title}")
    st.write(f"**Job Description:** {description}")
    st.write(f"**Required Skills:** {skills}")
    st.write(f"**Date Posted:** {posted_date}")
    st.write(f"**Last Date to Apply:** {last_date_to_apply}")

    with db.connect() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT full_name FROM users WHERE id = %s', (user_id,))
            result = cur.fetchone()
            candidate_name = result[0] if result else "Unknown User"

    st.write(f"**Applying as:** {candidate_name}")

    if f"application_submitted_{job_id}" not in st.session_state:
        st.session_state[f"application_submitted_{job_id}"] = False

    cvs = cv_service.get_cvs(user_id)
    if cvs:
        if not st.session_state[f"application_submitted_{job_id}"]:
            cv_list = [f"{cv[1]} (ATS Score: {cv[2]})" for cv in cvs]
            selected_cv = st.selectbox("Select Your Uploaded CV", cv_list, key=f"cv_select_{job_id}")
            selected_cv_id = cvs[cv_list.index(selected_cv)][0]

            submit_button = st.button("Submit Application", key=f"submit_{job_id}")

            if submit_button:
                resume_service.add_resume(job_id, candidate_name, selected_cv_id)
                resume_service.mark_job_as_applied(job_id, user_id)
                st.success(f"Your application for {title} has been successfully submitted!")
                st.session_state[f"application_submitted_{job_id}"] = True
        else:
            st.info("You have already submitted an application for this job.")
    else:
        st.warning("No CVs uploaded. Please upload a CV first under 'Upload CV'.")

def user_view(auth_service, job_service, resume_service):
    user = st.session_state.get("user", {})
    if not user:
        st.error("User information is missing. Please log in again.")
        st.stop()

    user_id = user.get("id")
    full_name = user.get("name")
    email = user.get("email")

    db = Database()
    cv_service = CVService(db)
    ats_evaluator = ATSEvaluator()

    with st.sidebar:
        selected = option_menu(
            menu_title="User Menu",
            options=["Upload CV", "Jobs", "View Applied Jobs", "Messages", "Chatbot", "ATS Evaluation", "CV Builder", "Manage Profile", "Logout"],
            icons=["upload", "briefcase", "list", "envelope", "chat-dots", "search", "file-text", "person", "box-arrow-right"],
            menu_icon="menu-button",
            default_index=0,
            orientation="vertical",
        )

    if selected == "Upload CV":
        st.header("CV Upload and Management", divider="blue")
        import cv_upload
        cv_upload.run_cv_upload()

    elif selected == "Jobs":
        st.header("Available Jobs", divider="blue")

        st.subheader("Filter Jobs")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            company_filter = st.text_input("Company Name", "")
        with col2:
            title_filter = st.text_input("Job Title", "")
        with col3:
            skills_filter = st.text_input("Skills (comma-separated)", "")
        with col4:
            last_date_filter = st.date_input("Last Date (on or after)", value=None, key="last_date_available")

        jobs = job_service.get_jobs(user_id)
        applied_jobs = resume_service.get_applied_jobs_for_user(user_id)

        if jobs:
            filtered_jobs = jobs
            if company_filter:
                filtered_jobs = [job for job in filtered_jobs if company_filter.lower() in str(job[2]).lower()]
            if title_filter:
                filtered_jobs = [job for job in filtered_jobs if title_filter.lower() in str(job[1]).lower()]
            if skills_filter:
                skill_list = [s.strip().lower() for s in skills_filter.split(",")]
                filtered_jobs = [job for job in filtered_jobs if any(skill in str(job[4]).lower() for skill in skill_list)]
            if last_date_filter:
                filtered_jobs = [job for job in filtered_jobs if job[6] and job[6] >= last_date_filter]

            if filtered_jobs:
                for job in filtered_jobs:
                    try:
                        job_id, title, company, description, skills, posted_date, last_date_to_apply = job
                    except ValueError as e:
                        st.error(f"Job data for job_id {job[0]} is incomplete: {e}. Skipping this job.")
                        continue

                    if job_id not in [applied_job[0] for applied_job in applied_jobs]:
                        with st.container(border=True):
                            st.write(f"### {title} - {company}")
                            st.write(f"{description[:200]}...")
                            view_button_key = f"view_{job_id}"
                            if st.button(f"View Job Details", key=view_button_key):
                                apply_for_job(job_id, title, company, description, skills, posted_date, last_date_to_apply, cv_service, user_id, resume_service, db)
            else:
                st.info("No jobs match your filters.")
        else:
            st.info("No jobs available.")

    elif selected == "View Applied Jobs":
        st.header("Your Applied Jobs", divider="blue")

        st.subheader("Filter Applied Jobs")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            company_filter_applied = st.text_input("Company Name", "", key="company_applied")
        with col2:
            title_filter_applied = st.text_input("Job Title", "", key="title_applied")
        with col3:
            skills_filter_applied = st.text_input("Skills (comma-separated)", "", key="skills_applied")
        with col4:
            last_date_filter_applied = st.date_input("Last Date (on or after)", value=None, key="last_date_applied")

        applied_jobs = resume_service.get_applied_jobs_for_user(user_id)

        if applied_jobs:
            filtered_applied_jobs = applied_jobs
            if company_filter_applied:
                filtered_applied_jobs = [job for job in filtered_applied_jobs if company_filter_applied.lower() in str(job[2]).lower()]
            if title_filter_applied:
                filtered_applied_jobs = [job for job in filtered_applied_jobs if title_filter_applied.lower() in str(job[1]).lower()]
            if skills_filter_applied:
                skill_list = [s.strip().lower() for s in skills_filter_applied.split(",")]
                filtered_applied_jobs = [job for job in filtered_applied_jobs if any(skill in str(job[4]).lower() for skill in skill_list)]
            if last_date_filter_applied:
                filtered_applied_jobs = [job for job in filtered_applied_jobs if job[6] and job[6] >= last_date_filter_applied]

            if filtered_applied_jobs:
                for job in filtered_applied_jobs:
                    try:
                        job_id, title, company, description, skills, posted_date, last_date_to_apply = job
                    except ValueError as e:
                        st.error(f"Applied job data for job_id {job[0]} is incomplete: {e}. Skipping this job.")
                        continue

                    with st.container(border=True):
                        st.write(f"### {title} - {company}")
                        st.write(f"{description[:200]}...")
                        view_button_key = f"view_applied_{job_id}"
                        if st.button(f"View Applied Job Details", key=view_button_key):
                            view_applied_job_dialog(job_id, title, company, description, skills, posted_date, last_date_to_apply, resume_service, cv_service, user_id)
            else:
                st.info("No applied jobs match your filters.")
        else:
            st.info("You have not applied to any jobs yet.")

    elif selected == "Chatbot":
        st.header("Chat with Your CV", divider="blue")
        chatbot = Chatbot()
        chatbot.run()

    elif selected == "ATS Evaluation":
        st.header("ATS Evaluation of Your CV", divider="blue")
        ats_evaluation = ATSEvaluator()
        ats_evaluation.run()

    elif selected == "Messages":
        st.header("Messages from HR", divider="blue")
        with resume_service.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT hr_messages.message, hr_messages.sent_at, users.full_name, jobs.title
                    FROM hr_messages
                    JOIN users ON hr_messages.hr_id = users.id
                    JOIN jobs ON hr_messages.job_id = jobs.id
                    WHERE hr_messages.candidate_id = %s
                    ORDER BY hr_messages.sent_at DESC
                    ''',
                    (user_id,)
                )
                messages = cur.fetchall()

        if messages:
            for message, sent_at, hr_name, job_title in messages:
                with st.expander(f"Message from {hr_name} for {job_title} ({sent_at.strftime('%Y-%m-%d %H:%M:%S')})"):
                    if "**Job Description:**" in message:
                        custom_message, jd = message.split("**Job Description:**", 1)
                        st.write(custom_message.strip())
                        if st.button("Show Job Description", key=f"jd_{sent_at}_{hr_name}"):
                            show_jd_dialog(jd)
                    else:
                        st.write(message)
        else:
            st.info("No messages received yet.")

    elif selected == "Manage Profile":
        manageprofile_col1, manageprofile_col2 = st.columns([0.30, 0.70])
        with manageprofile_col1:
            st.image("static/manageprofile.png", width=400)

        with manageprofile_col2:
            st.header("Manage Your Profile", divider="blue")
            try:
                updated_full_name = st.text_input("Full Name", value=full_name, key="profile_full_name")
                updated_email = st.text_input("Email", value=email, key="profile_email")
                new_password = st.text_input("New Password (optional)", type="password", key="profile_password")

                if st.button("Save Changes"):
                    if not updated_full_name or not updated_email:
                        st.warning("Full Name and Email cannot be empty.")
                    elif not auth_service.is_valid_email(updated_email):
                        st.error("Invalid email format. Please enter a valid email.")
                    elif new_password and not auth_service.is_valid_password(new_password):
                        st.error(
                            "Password does not meet the criteria. "
                            "It must be at least 8 characters long, contain letters, numbers, and at least one special character."
                        )
                    else:
                        auth_service.update_user(
                            account_id=user_id,
                            full_name=updated_full_name,
                            email=updated_email,
                            password=new_password if new_password else None,
                        )
                        st.session_state["user"]["name"] = updated_full_name
                        st.session_state["user"]["email"] = updated_email
                        st.success("Profile updated successfully.")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")

    elif selected == "CV Builder":
            st.header("Build Your CV", divider="blue")
            st.write("Use the embedded CV builder below to create your CV instantly. No login required!")
            
            iframe_code = """
            <iframe 
                src="https://www.open-resume.com/resume-builder" 
                width="100%" 
                height="800px" 
                frameborder="0"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            ></iframe>
            """
            components.html(iframe_code, height=1600)

            st.markdown(
                """
                <style>
                .border-gray-100 {
                    display: none;
                    }
            
                </style>
                """,
                unsafe_allow_html=True,
            )
    

    elif selected == "Logout":
        st.session_state.clear()
        st.success("Logged out successfully.")
        st.rerun()