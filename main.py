import streamlit as st
from streamlit_option_menu import option_menu
from db import Database
from auth import AuthService
from ats import JobService, ResumeService
from admin import admin_view
from hr import hr_view
from user import user_view
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

db = Database()
db.initialize()
auth_service = AuthService(db)
job_service = JobService(db)
resume_service = ResumeService(db)

st.set_page_config(page_title="HIREZY", page_icon=":briefcase:")

st.markdown(
    """
    <style>
    .st-emotion-cache-11qx4gg { display: none; }
    .st-emotion-cache-13ln4jf { max-width: 95rem; padding: 3rem 1rem 10rem; }
    .st-emotion-cache-12fmjuu { display: none; }
    .st-emotion-cache-1u2dcfn { display: none; }
    .st-emotion-cache-6awftf { display: none; }
    .st-emotion-cache-gi0tri { display: none; }
    .st-emotion-cache-1eo1tir { width: 100%; padding: 3rem 1rem 1rem; max-width: 90rem; }
    .border-gray-100 { display: none; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "password_valid" not in st.session_state:
    st.session_state["password_valid"] = None
if "passwords_match_user" not in st.session_state:
    st.session_state["passwords_match_user"] = None
if "passwords_match_hr" not in st.session_state:
    st.session_state["passwords_match_hr"] = None
if "username_available" not in st.session_state:
    st.session_state["username_available"] = True
if "email_available" not in st.session_state:
    st.session_state["email_available"] = True
if "hr_phase_1_complete" not in st.session_state:
    st.session_state["hr_phase_1_complete"] = False
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "Login"

def validate_user_password():
    password = st.session_state.get("register_user_password", "")
    st.session_state["password_valid"] = AuthService.is_valid_password(password)
    validate_user_confirm_password()

def validate_user_confirm_password():
    st.session_state["passwords_match_user"] = (
        st.session_state.get("register_user_password", "") == st.session_state.get("register_user_confirm_password", "")
    )

def validate_hr_password():
    password = st.session_state.get("register_hr_password", "")
    st.session_state["password_valid"] = AuthService.is_valid_password(password)
    validate_hr_confirm_password()

def validate_hr_confirm_password():
    st.session_state["passwords_match_hr"] = (
        st.session_state.get("register_hr_password", "") == st.session_state.get("register_hr_confirm_password", "")
    )

def check_username(username_key):
    username = st.session_state.get(username_key, "")
    st.session_state["username_available"] = not auth_service.check_username_exists(username)

def check_email(email_key, role="User"):
    email = st.session_state.get(email_key, "")
    blocked_domains = ["gmail.com", "outlook.com", "hotmail.com", "yahoo.com"] if role == "HR" else []
    domain = email.split("@")[-1] if "@" in email else ""
    if role == "HR" and domain in blocked_domains:
        st.session_state["email_available"] = False
    else:
        st.session_state["email_available"] = AuthService.is_valid_email(email) and not auth_service.check_email_exists(email)

if not st.session_state["logged_in"]:
    authcol1, authcol2 = st.columns([0.60, 0.40])
    with authcol1:
        st.image("static/auth.png", width=700, caption="Evaluate your Resume Securely")

    with authcol2:
        tab_login, tab_register = st.tabs(["Login", "Register"])
        if tab_login:
            st.session_state["active_tab"] = "Login"
        elif tab_register:
            st.session_state["active_tab"] = "Register"

        with tab_login:
            st.subheader("Login")
            login_identifier = st.text_input("Username or Email", key="login_identifier")
            password = st.text_input("Password", type="password", key="login_password")
    
            if st.button("Login", key="login_button", type="primary"):
                try:
                    user = auth_service.authenticate_user(login_identifier, password)
                    if user:
                        st.session_state["logged_in"] = True
                        st.session_state["user"] = {
                            "id": user[0], "name": user[1], "username": user[2], "email": user[3], "role": user[4],
                            "company_name": user[5], "contact_number": user[6], "cnic": user[7], "designation": user[8],
                            "company_type": user[9], "company_address": user[10], "company_contact_number": user[11],
                            "company_website": user[12], "hr_role_in_company": user[13], "is_approved": user[14]
                        }
                        st.rerun()
                    else:
                        st.error("Invalid username/email or password. Please try again.")
                except ValueError as e:
                    st.error(str(e))
    
        with tab_register:
            tab_register_user, tab_register_hr = st.tabs(["Register as User", "Register as HR"])
    
            with tab_register_user:
                st.subheader("Register as User")
                full_name = st.text_input("Full Name *", key="register_user_full_name")
                username = st.text_input("Username *", key="register_user_username", on_change=check_username, args=("register_user_username",))
                email = st.text_input("Email *", key="register_user_email", on_change=check_email, args=("register_user_email",))
                industry = st.selectbox("Industry *", ["Software", "Finance", "Healthcare", "Education"], key="register_user_industry")
                password = st.text_input("Password *", type="password", key="register_user_password", on_change=validate_user_password)
                confirm_password = st.text_input("Confirm Password *", type="password", key="register_user_confirm_password", on_change=validate_user_confirm_password)
    
                if not st.session_state.get("username_available", True):
                    st.error("Username is already taken.")
                if not st.session_state.get("email_available", True):
                    st.error("Invalid or already registered email.")
                if st.session_state.get("passwords_match_user") is False:
                    st.error("Passwords do not match.")
                if st.session_state.get("password_valid") is False:
                    st.error("Password must be 8+ characters with letters, numbers, and special characters (@$!%*?&#).")
        
                register_disabled = not (
                    full_name and username and email and industry and password and confirm_password and
                    st.session_state.get("username_available", True) and
                    st.session_state.get("email_available", True) and
                    st.session_state.get("passwords_match_user", True) and
                    st.session_state.get("password_valid", True)
                )
    
                if st.button("Register as User", disabled=register_disabled, type="primary"):
                    logger.debug("User registration button clicked")
                    result = auth_service.register_user(full_name, username, email, password, None, "User")
                    logger.debug(f"Registration result: {result}")
                    if result and result.get("success"):
                        st.success("User registration successful! Please log in.")
                        
                    else:
                        st.error(result.get("error", "An error occurred during registration."))
    
            with tab_register_hr:
                st.subheader("Register as HR")
                if not st.session_state["hr_phase_1_complete"]:
                    st.write("##### Personal Information")
                    full_name_hr = st.text_input("Full Name *", key="register_hr_full_name")
                    username_hr = st.text_input("Username *", key="register_hr_username", on_change=check_username, args=("register_hr_username",))
                    email_hr = st.text_input("Company Email *", key="register_hr_email", on_change=check_email, args=("register_hr_email", "HR"))
                    contact_number_hr = st.text_input("Contact Number *", key="register_hr_contact_number")
                    cnic_hr = st.text_input("CNIC/Identification Number *", key="register_hr_cnic")
                    designation_hr = st.selectbox("Designation *", ["HR Manager", "Talent Acquisition Specialist", "Recruiter", "Other"], key="register_hr_designation")
                    password_hr = st.text_input("Password *", type="password", key="register_hr_password", on_change=validate_hr_password)
                    confirm_password_hr = st.text_input("Confirm Password *", type="password", key="register_hr_confirm_password", on_change=validate_hr_confirm_password)

                    if not st.session_state.get("username_available", True):
                        st.error("Username is already taken.")
                    if not st.session_state.get("email_available", True):
                        st.error("Invalid or already registered email. Use a company email (no Gmail, Outlook, etc.).")
                    if st.session_state.get("passwords_match_hr") is False:
                        st.error("Passwords do not match.")
                    if st.session_state.get("password_valid") is False:
                        st.error("Password must be 8+ characters with letters, numbers, and special characters (@$!%*?&#).")

                    if st.button("Next: Company Details", type="primary"):
                        if not all([full_name_hr, username_hr, email_hr, contact_number_hr, cnic_hr, designation_hr, password_hr, confirm_password_hr]):
                            st.warning("All fields are required.")
                        elif not st.session_state.get("username_available", True):
                            st.error("Username is already taken.")
                        elif not st.session_state.get("email_available", True):
                            st.error("Invalid email or company email required.")
                        elif not st.session_state["passwords_match_hr"]:
                            st.error("Passwords do not match.")
                        elif not st.session_state["password_valid"]:
                            st.error("Password must be 8+ characters with letters, numbers, and special characters (@$!%*?&#).")
                        else:
                            st.session_state["hr_phase_1_data"] = {
                                "full_name": full_name_hr, "username": username_hr, "email": email_hr,
                                "contact_number": contact_number_hr, "cnic": cnic_hr, "designation": designation_hr,
                                "password": password_hr
                            }
                            st.session_state["hr_phase_1_complete"] = True
                            st.rerun()
                else:
                    st.write("##### Company Details")
                    company_name_hr = st.text_input("Company Name *", key="register_hr_company_name")
                    company_type_hr = st.selectbox("Company Type *", ["IT", "Finance", "Manufacturing", "Other"], key="register_hr_company_type")
                    company_address_hr = st.text_area("Company Address *", key="register_hr_company_address")
                    company_contact_number_hr = st.text_input("Company Contact Number *", key="register_hr_company_contact_number")
                    company_website_hr = st.text_input("Company Website *", key="register_hr_company_website")
                    hr_role_in_company_hr = st.text_input("Your Role in Company *", key="register_hr_role_in_company")

                    if st.button("Register as HR", type="primary"):
                        if not all([company_name_hr, company_type_hr, company_address_hr, company_contact_number_hr, company_website_hr, hr_role_in_company_hr]):
                            st.warning("All fields are required.")
                        else:
                            phase_1_data = st.session_state["hr_phase_1_data"]
                            result = auth_service.register_user(
                                phase_1_data["full_name"], phase_1_data["username"], phase_1_data["email"],
                                phase_1_data["password"], company_name_hr, "HR", phase_1_data["contact_number"],
                                phase_1_data["cnic"], phase_1_data["designation"], company_type_hr,
                                company_address_hr, company_contact_number_hr, company_website_hr, hr_role_in_company_hr
                            )
                            logger.debug(f"HR Registration result: {result}")
                            if result and result.get("success"):
                                st.success("HR registration successful! Awaiting Admin approval.")

                                
                            else:
                                st.error(result.get("error", "An error occurred during HR registration."))

else:
    with st.sidebar:
        st.image("static/hirezy-logo.png")
    
    user = st.session_state.get("user", {})
    user_role = user.get("role", "")
    user_name = user.get("name", "")

    if not user_role:
        st.error("User role is missing. Please log in again.")
        st.stop()

    st.sidebar.header(f"Welcome, {user_name}")

    if user_role == "Admin":
        admin_view(auth_service)
    elif user_role == "HR":
        hr_view(auth_service, job_service, resume_service)
    elif user_role == "User":
        user_view(auth_service, job_service, resume_service)