from db import Database
import streamlit as st

class JobService:
    def __init__(self, db: Database):
        self.db = db

    def add_job(self, company_name, title, description, skills, uploaded_date, last_date_to_apply, hr_id):
        """Add a new job to the database."""
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''INSERT INTO jobs (company_name, title, description, skills, uploaded_date, last_date_to_apply, hr_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                    (company_name, title, description, skills, uploaded_date, last_date_to_apply, hr_id)
                )
                conn.commit()

    def get_jobs(self, user_id):
        """Retrieve all available jobs, excluding jobs the current user has applied for, ordered by last date to apply."""
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT j.id, j.company_name, j.title, j.description, j.skills, j.uploaded_date, j.last_date_to_apply
                    FROM jobs j
                    LEFT JOIN applied_jobs a ON j.id = a.job_id AND a.user_id = %s
                    WHERE a.job_id IS NULL
                    ORDER BY j.last_date_to_apply DESC
                ''', (user_id,))
                return cur.fetchall()

    def delete_job(self, job_id):
        """Delete a job from the database."""
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM jobs WHERE id = %s', (job_id,))
                conn.commit()

    def get_jobs_for_hr(self, hr_id):
            with self.db.connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, company_name, title, description, skills, uploaded_date, last_date_to_apply FROM jobs WHERE hr_id = %s ORDER BY uploaded_date DESC",
                        (hr_id,)
                    )
                    return cur.fetchall()
    
    def get_job_by_id(self, job_id):
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT company_name, title, description, skills FROM jobs WHERE id = %s",
                    (job_id,)
                )
                return cur.fetchone()


class ResumeService:
    def __init__(self, db: Database):
        self.db = db

    def add_resume(self, job_id, candidate_name, cv_id):
        """Add a new resume entry for a job application."""
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO resumes (job_id, candidate_name, cv) VALUES (%s, %s, %s)',
                    (job_id, candidate_name, cv_id)
                )
                conn.commit()

    def get_applied_jobs_for_user(self, user_id):
        """Fetch all jobs a user has applied to with full job details."""
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT 
                        j.id, 
                        j.title, 
                        j.company_name, 
                        j.description, 
                        j.skills, 
                        j.uploaded_date, 
                        j.last_date_to_apply
                    FROM jobs j
                    INNER JOIN applied_jobs a ON j.id = a.job_id
                    WHERE a.user_id = %s
                    ORDER BY a.applied_at DESC
                    ''',
                    (user_id,)
                )
                return cur.fetchall()

    def mark_job_as_applied(self, job_id, user_id):
        """Mark a job as applied by the user."""
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO applied_jobs (user_id, job_id)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id, job_id) DO NOTHING
                ''', (user_id, job_id))
                conn.commit()


    def get_resumes_for_job(self, job_id):
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT resumes.id, resumes.job_id, resumes.candidate_name, user_cvs.cv_data, resumes.is_selected,
                           resumes.evaluation_score, resumes.evaluation_comments, user_cvs.user_id, user_cvs.file_name
                    FROM resumes
                    JOIN user_cvs ON resumes.cv = user_cvs.id
                    WHERE resumes.job_id = %s
                    ''',
                    (job_id,)
                )
                return cur.fetchall()

    def update_resume_evaluation(self, resume_id, score, comments, is_selected=False):
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE resumes SET evaluation_score = %s, evaluation_comments = %s, is_selected = %s WHERE id = %s",
                    (score, comments, is_selected, resume_id)
                )
                conn.commit()

    def send_message_to_candidate(self, hr_id, candidate_id, job_id, message):
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO hr_messages (hr_id, candidate_id, job_id, message) VALUES (%s, %s, %s, %s)",
                    (hr_id, candidate_id, job_id, message)
                )
                conn.commit()

    def get_selected_resumes_for_job(self, job_id):
        with self.db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT resumes.id, resumes.candidate_name, user_cvs.cv_data, user_cvs.user_id, user_cvs.file_name
                    FROM resumes
                    JOIN user_cvs ON resumes.cv = user_cvs.id
                    WHERE resumes.job_id = %s AND resumes.is_selected = TRUE
                    ''',
                    (job_id,)
                )
                return cur.fetchall()