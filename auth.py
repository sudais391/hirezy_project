import hashlib
import psycopg2
from psycopg2 import errors
from db import Database


class AuthService:
    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, full_name, username, email, password, company_name, role_name="User", contact_number=None, cnic=None, designation=None, company_type=None, company_address=None, company_contact_number=None, company_website=None, hr_role_in_company=None):
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT id FROM roles WHERE name = %s', (role_name,))
                role = cur.fetchone()
                if not role:
                    return {"success": False, "error": f"Role '{role_name}' not found. Ensure roles are initialized."}

                hashed_password = self.hash_password(password)

                try:
                    cur.execute(
                        '''
                        INSERT INTO users (
                            full_name, username, email, password, role_id, company_name,
                            contact_number, cnic, designation, company_type, company_address,
                            company_contact_number, company_website, hr_role_in_company,
                            is_approved
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ''',
                        (
                            full_name, username, email, hashed_password, role[0], company_name,
                            contact_number, cnic, designation, company_type, company_address,
                            company_contact_number, company_website, hr_role_in_company,
                            False if role_name == "HR" else True
                        )
                    )
                    conn.commit()
                    return {"success": True, "error": None}
                except errors.UniqueViolation as e:
                    conn.rollback()
                    if "users_username_key" in str(e):
                        return {"success": False, "error": "The username is already taken. Please choose another."}
                    if "users_email_key" in str(e):
                        return {"success": False, "error": "The email is already registered. Please use a different email."}
                    if "users_cnic_key" in str(e):
                        return {"success": False, "error": "The CNIC is already registered. Please use a different CNIC."}
                    return {"success": False, "error": "A database error occurred. Please try again."}
                except Exception as e:
                    conn.rollback()
                    return {"success": False, "error": f"An unexpected error occurred: {str(e)}"}

    def update_user(self, account_id, full_name, email, password=None, industry=None, company_name=None, contact_number=None, cnic=None, designation=None, company_type=None, company_address=None, company_contact_number=None, company_website=None, hr_role_in_company=None, is_approved=None):
        allowed_industries = ["Software", "Finance", "Healthcare", "Education"]
        
        if not self.is_valid_email(email):
            raise ValueError("Invalid email format.")
        
        if industry and industry not in allowed_industries:
            raise ValueError("Invalid industry value.")
        
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                update_fields = []
                update_values = []
        
                if full_name:
                    update_fields.append("full_name = %s")
                    update_values.append(full_name)
                if email:
                    update_fields.append("email = %s")
                    update_values.append(email)
                if password:
                    update_fields.append("password = %s")
                    update_values.append(self.hash_password(password))
                if industry is not None:
                    update_fields.append("industry = %s")
                    update_values.append(industry)
                if company_name is not None:
                    update_fields.append("company_name = %s")
                    update_values.append(company_name)
                if contact_number is not None:
                    update_fields.append("contact_number = %s")
                    update_values.append(contact_number)
                if cnic is not None:
                    update_fields.append("cnic = %s")
                    update_values.append(cnic)
                if designation is not None:
                    update_fields.append("designation = %s")
                    update_values.append(designation)
                if company_type is not None:
                    update_fields.append("company_type = %s")
                    update_values.append(company_type)
                if company_address is not None:
                    update_fields.append("company_address = %s")
                    update_values.append(company_address)
                if company_contact_number is not None:
                    update_fields.append("company_contact_number = %s")
                    update_values.append(company_contact_number)
                if company_website is not None:
                    update_fields.append("company_website = %s")
                    update_values.append(company_website)
                if hr_role_in_company is not None:
                    update_fields.append("hr_role_in_company = %s")
                    update_values.append(hr_role_in_company)
                if is_approved is not None:
                    update_fields.append("is_approved = %s")
                    update_values.append(is_approved)
        
                if not update_fields:
                    return
        
                update_query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
                update_values.append(account_id)
        
                cur.execute(update_query, tuple(update_values))
        
                if cur.rowcount == 0:
                    raise ValueError("User not found or no changes detected.")
        
                conn.commit()
    
    def get_hr_details(self, hr_id):
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT full_name, email
                    FROM users
                    WHERE id = %s
                    ''',
                    (hr_id,)
                )
                row = cur.fetchone()
                if row:
                    return {"full_name": row[0], "email": row[1]}
                else:
                    raise ValueError("HR details not found.")

    def get_user_id(self, username):
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE username = %s", (username,))
                result = cur.fetchone()
                if result:
                    return result[0]
                else:
                    raise ValueError(f"No user found with username: {username}")
    
    def authenticate_user(self, identifier, password):
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                hashed_password = self.hash_password(password)
                cur.execute(
                    '''
                    SELECT users.id, users.full_name, users.username, users.email, roles.name AS role,
                           users.company_name, users.contact_number, users.cnic, users.designation,
                           users.company_type, users.company_address, users.company_contact_number,
                           users.company_website, users.hr_role_in_company, users.is_approved
                    FROM users
                    INNER JOIN roles ON users.role_id = roles.id
                    WHERE (users.username = %s OR users.email = %s) AND users.password = %s
                    ''',
                    (identifier, identifier, hashed_password)
                )
                user = cur.fetchone()
                if user and user[4] == "HR" and not user[14]: 
                    raise ValueError("Your HR account is pending approval by an Admin.")
                return user
    
    def check_username_exists(self, username):
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT username FROM users WHERE username = %s", (username,))
                return cur.fetchone() is not None

    def check_email_exists(self, email):
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT email FROM users WHERE email = %s", (email,))
                return cur.fetchone() is not None

    def get_all_hr_accounts(self):
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT users.id AS user_id, users.full_name, users.username, users.email, users.registered_at
                    FROM users
                    INNER JOIN roles ON users.role_id = roles.id
                    WHERE roles.name = 'HR'
                    ORDER BY users.registered_at DESC
                    '''
                )
                return cur.fetchall()

    def get_all_user_accounts(self):
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT users.id AS user_id, users.full_name, users.username, users.email, users.industry, users.registered_at
                    FROM users
                    INNER JOIN roles ON users.role_id = roles.id
                    WHERE roles.name = 'User'
                    ORDER BY users.registered_at DESC
                    '''
                )
                return cur.fetchall()

    def delete_user(self, user_id):
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM jobs WHERE hr_id = %s", (user_id,))
                job_count = cur.fetchone()[0]
                
                if job_count > 0:
                    cur.execute("DELETE FROM jobs WHERE hr_id = %s", (user_id,))
                
                cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
        return job_count 
  
    @staticmethod
    def is_valid_email(email):
        import re
        email_regex = (
            r"^(?!\.)"
            r"[a-zA-Z0-9_.+-]+"
            r"(?<!\.)@"
            r"[a-zA-Z0-9-]+"
            r"(\.[a-zA-Z]{2,})+$"
        )
        return bool(re.match(email_regex, email)) and ".." not in email

    @staticmethod
    def is_valid_password(password):
        import re
        if len(password) < 8:
            return False
        if not re.search(r"[a-zA-Z]", password):
            return False
        if not re.search(r"[0-9]", password):
            return False
        if not re.search(r"[@$!%*?&#]", password):
            return False
        return True