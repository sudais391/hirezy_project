import streamlit as st
from streamlit_option_menu import option_menu
from chatbot import Chatbot
from datetime import datetime
import zipfile
from io import BytesIO

def hr_view(auth_service, job_service, resume_service):
    user = st.session_state.get("user", {})
    if not user:
        st.error("User information is missing. Please log in again.")
        st.stop()

    hr_id = user.get("id")
    full_name = user.get("name")
    email = user.get("email")
    company_name = user.get("company_name")
    designation = user.get("designation")
    company_type = user.get("company_type")
    company_address = user.get("company_address")
    company_website = user.get("company_website")
    hr_role_in_company = user.get("hr_role_in_company")

    with st.sidebar:
        selected = option_menu(
            menu_title="HR Menu",
            options=["Post Job", "View Posted Jobs", "Evaluate Resumes", "Send Messages", "Chatbot", "Manage Profile", "Logout"],
            icons=["briefcase", "list", "clipboard-check", "envelope", "chat-dots", "person", "box-arrow-right"],
            menu_icon="people",
            default_index=0,
            orientation="vertical",
        )

    if selected == "Post Job":
        if not company_name:
            st.warning("You cannot post a job without setting your company name. Please update your profile.")
            return

        st.header("Post a New Job", divider="blue")
        job_title = st.text_input("Job Title", key="job_title")
        job_description = st.text_area("Job Description", key="job_description")
        required_skills = st.text_input("Required Skills (comma separated)", key="job_skills")
        last_date_to_apply = st.date_input("Last Date to Apply", key="last_date_to_apply", min_value=datetime.today().date())
        uploaded_date = datetime.today().strftime('%Y-%m-%d')

        if st.button("Post Job"):
            if not all([job_title, job_description, required_skills, last_date_to_apply]):
                st.warning("Please fill out all fields before posting the job.")
            else:
                job_service.add_job(company_name, job_title, job_description, required_skills, uploaded_date, last_date_to_apply, hr_id)
                st.success("Job posted successfully!")

    elif selected == "View Posted Jobs":
        st.header("View Posted Jobs", divider="blue")
        fil_col1, fil_col2 = st.columns(2)
        with fil_col1:
            search_query = st.text_input("Search for a job by title or company", "")
        with fil_col2:
            filter_by_skills = st.text_input("Filter by Required Skills (comma separated)", "")

        jobs = job_service.get_jobs_for_hr(hr_id)
        if search_query:
            jobs = [job for job in jobs if search_query.lower() in job[1].lower() or search_query.lower() in job[2].lower()]
        if filter_by_skills:
            filter_skills = set(filter_by_skills.lower().split(","))
            jobs = [job for job in jobs if filter_skills.issubset(set(job[4].lower().split(",")))]

        if jobs:
            for job in jobs:
                with st.expander(job[2]):
                    st.write(f"**Company:** {job[1]}")
                    st.subheader(job[2])
                    st.write(f"**Description:** {job[3]}")
                    st.write(f"**Required Skills:** {job[4]}")
                    st.write(f"**Uploaded on:** {job[5]}")
                    st.write(f"**Last Date to Apply:** {job[6]}")
                    if st.button(f"Delete Job: {job[2]}", key=f"delete_{job[0]}"):
                        job_service.delete_job(job[0])
                        st.success(f"Job '{job[2]}' deleted successfully.")
                        st.rerun()
        else:
            st.write("No jobs match the current filters or search query.")

    elif selected == "Evaluate Resumes":
        st.header("Evaluate Candidates for a Job", divider="blue")
        jobs = job_service.get_jobs_for_hr(hr_id)
        if jobs:
            job_list = [f"{job[1]} - {job[2]}" for job in jobs]
            selected_job = st.selectbox("Select Job", job_list, key="selected_job")
            selected_job_id = jobs[job_list.index(selected_job)][0]
            resumes = resume_service.get_resumes_for_job(selected_job_id)

            if resumes:
                st.subheader("Resumes Submitted")
                for resume in resumes:
                    resume_id, job_id, candidate_name, cv_data, is_selected, score, comments, candidate_id, file_name = resume
                    with st.expander(f"Candidate: {candidate_name}"):
                        st.write("**Resume Content:**")
                        try:
                            display_data = cv_data.tobytes() if isinstance(cv_data, memoryview) else cv_data
                            st.text(display_data.decode('utf-8') if isinstance(display_data, bytes) else display_data)
                        except Exception:
                            st.write("(Binary resume data - display not supported yet)")

                        st.write("**Evaluation:**")
                        eval_score = st.slider("Score (0-100)", 0, 100, score if score else 0, key=f"score_{resume_id}")
                        eval_comments = st.text_area("Comments", value=comments if comments else "", key=f"comments_{resume_id}")
                        is_selected_check = st.checkbox("Select Candidate", value=is_selected, key=f"select_{resume_id}")

                        if st.button("Save Evaluation", key=f"save_{resume_id}"):
                            resume_service.update_resume_evaluation(resume_id, eval_score, eval_comments, is_selected_check)
                            st.success(f"Evaluation for {candidate_name} saved successfully.")
                            st.rerun()

                        if cv_data:
                            download_data = cv_data.tobytes() if isinstance(cv_data, memoryview) else cv_data
                            st.download_button(
                                label=f"Download {candidate_name}'s CV",
                                data=download_data,
                                file_name=file_name or f"{candidate_name}_cv.pdf",
                                mime="application/pdf",
                                key=f"download_{resume_id}"
                            )

                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for resume in resumes:
                        resume_id, job_id, candidate_name, cv_data, is_selected, score, comments, candidate_id, file_name = resume
                        if cv_data:
                            zip_data = cv_data.tobytes() if isinstance(cv_data, memoryview) else cv_data
                            zip_file.writestr(file_name or f"{candidate_name}_cv.pdf", zip_data)
                zip_buffer.seek(0)
                st.download_button(
                    label="Download All CVs as ZIP",
                    data=zip_buffer,
                    file_name=f"job_{selected_job_id}_cvs.zip",
                    mime="application/zip",
                    key="download_all_zip"
                )
            else:
                st.info("No resumes uploaded yet for this job.")
        else:
            st.info("No jobs available to evaluate resumes.")

    elif selected == "Send Messages":
        st.header("Send Messages to Selected Candidates", divider="blue")
        jobs = job_service.get_jobs_for_hr(hr_id)
        if jobs:
            job_list = [f"{job[1]} - {job[2]}" for job in jobs]
            selected_job = st.selectbox("Select Job", job_list, key="message_selected_job")
            selected_job_id = jobs[job_list.index(selected_job)][0]
            selected_resumes = resume_service.get_selected_resumes_for_job(selected_job_id)

            if selected_resumes:
                st.subheader(f"Selected Candidates for {selected_job}")
                for resume in selected_resumes:
                    resume_id, candidate_name, cv_data, candidate_id, file_name = resume
                    st.write(f"- {candidate_name}")

                message = st.text_area("Message to Selected Candidates", value="Congratulations! You've been selected for an interview. Please reply to schedule.", key="bulk_message")
                if st.button("Send Message to All Selected", key="send_all"):
                    job_details = job_service.get_job_by_id(selected_job_id)
                    full_message = f"{message}\n\n**Job Description:**\nCompany: {job_details[0]}\nTitle: {job_details[1]}\nDescription: {job_details[2]}\nSkills: {job_details[3]}"
                    for resume in selected_resumes:
                        resume_id, candidate_name, cv_data, candidate_id, file_name = resume
                        resume_service.send_message_to_candidate(hr_id, candidate_id, selected_job_id, full_message)
                    st.success(f"Message sent to {len(selected_resumes)} selected candidate(s) successfully.")
            else:
                st.info("No candidates have been selected for this job yet. Please evaluate and select candidates in 'Evaluate Resumes'.")
        else:
            st.info("No jobs available to send messages for.")

    elif selected == "Chatbot":
        st.header("Chat with Candidate CV", divider="blue")
        chatbot = Chatbot()
        chatbot.run()

    elif selected == "Manage Profile":
        st.header("Manage Your Profile", divider="blue")
        phase_1_complete = all([full_name, email, designation])

        st.write("#### Personal Information")
        with st.form(key="phase_1_form"):
            updated_full_name = st.text_input("Full Name *", value=full_name or "", key="profile_full_name")
            updated_email = st.text_input("Email *", value=email or "", key="profile_email")
            updated_designation = st.selectbox("Designation *", ["HR Manager", "Talent Acquisition Specialist", "Recruiter", "Other"], index=["HR Manager", "Talent Acquisition Specialist", "Recruiter", "Other"].index(designation) if designation else 0, key="profile_designation")
            new_password = st.text_input("New Password (optional)", type="password", key="profile_password")

            submit_phase_1 = st.form_submit_button("Save")
            if submit_phase_1:
                if not all([updated_full_name, updated_email, updated_designation]):
                    st.warning("All fields are required.")
                elif not auth_service.is_valid_email(updated_email):
                    st.error("Invalid email format.")
                elif new_password and not auth_service.is_valid_password(new_password):
                    st.error("Password must be 8+ characters with letters, numbers, and a special character.")
                else:
                    try:
                        auth_service.update_user(
                            account_id=hr_id,
                            full_name=updated_full_name,
                            email=updated_email,
                            designation=updated_designation,
                            password=new_password if new_password else None
                        )
                        st.session_state["user"]["name"] = updated_full_name
                        st.session_state["user"]["email"] = updated_email
                        st.session_state["user"]["designation"] = updated_designation
                        st.success("Updated successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating: {e}")

        if phase_1_complete:
            st.write("#### Company Details")
            with st.form(key="phase_2_form"):
                updated_company_name = st.text_input("Company Name *", value=company_name or "", key="profile_company_name")
                updated_company_type = st.selectbox("Company Type *", ["IT", "Finance", "Manufacturing", "Other"], index=["IT", "Finance", "Manufacturing", "Other"].index(company_type) if company_type else 0, key="profile_company_type")
                updated_company_address = st.text_area("Company Address *", value=company_address or "", key="profile_company_address")
                updated_company_website = st.text_input("Company Website *", value=company_website or "", key="profile_company_website")
                updated_hr_role_in_company = st.text_input("Your Role in Company *", value=hr_role_in_company or "", key="profile_hr_role_in_company")

                submit_phase_2 = st.form_submit_button("Save")
                if submit_phase_2:
                    if not all([updated_company_name, updated_company_type, updated_company_address, updated_company_website, updated_hr_role_in_company]):
                        st.warning("All fields are required.")
                    else:
                        try:
                            auth_service.update_user(
                                account_id=hr_id,
                                company_name=updated_company_name,
                                company_type=updated_company_type,
                                company_address=updated_company_address,
                                company_website=updated_company_website,
                                hr_role_in_company=updated_hr_role_in_company
                            )
                            st.session_state["user"]["company_name"] = updated_company_name
                            st.session_state["user"]["company_type"] = updated_company_type
                            st.session_state["user"]["company_address"] = updated_company_address
                            st.session_state["user"]["company_website"] = updated_company_website
                            st.session_state["user"]["hr_role_in_company"] = updated_hr_role_in_company
                            st.success("Updated successfully.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating : {e}")
        else:
            st.info("Please complete (Personal Information) before proceeding to (Company Details).")

    elif selected == "Logout":
        st.session_state.clear()
        st.success("Logged out successfully.")
        st.rerun()