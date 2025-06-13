import psycopg2

class Database:
    def __init__(self, host="aws-0-ap-southeast-1.pooler.supabase.com", database="postgres", user="postgres.gzsvrlslnlcikuxeiqyu ", password="hirezy3421$", port="6543"):
        self.host = host
        self.database = database
        self.user = user
        self.password = password

    def connect(self):
        return psycopg2.connect(
            host=self.host,
            database=self.database,
            user=self.user,
            password=self.password
        )

    def initialize(self):
        with self.connect() as conn:
            with conn.cursor() as cur:
                self._create_tables(cur)
                self._initialize_roles(cur)
                self._initialize_admin(cur)
            conn.commit()

    def _create_tables(self, cur):
        cur.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE
            );
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                full_name TEXT,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                password TEXT,
                industry TEXT,
                role_id INTEGER REFERENCES roles(id),
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                company_name TEXT,
                contact_number TEXT,
                cnic TEXT UNIQUE,
                designation TEXT,
                company_type TEXT,
                company_address TEXT,
                company_contact_number TEXT,
                company_website TEXT,
                hr_role_in_company TEXT,
                is_approved BOOLEAN DEFAULT FALSE
            );
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                company_name TEXT,
                title TEXT,
                description TEXT,
                skills TEXT,
                uploaded_date DATE,
                last_date_to_apply DATE,
                hr_id INTEGER REFERENCES users(id) ON DELETE CASCADE
            );
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_cvs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                file_name TEXT,
                ats_score FLOAT,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cv_data BYTEA
            );
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS resumes (
                id SERIAL PRIMARY KEY,
                job_id INTEGER REFERENCES jobs(id),
                candidate_name TEXT,
                cv INTEGER REFERENCES user_cvs(id),
                is_selected BOOLEAN DEFAULT FALSE,
                evaluation_score INTEGER,
                evaluation_comments TEXT
            );
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS evaluation_results (
                id SERIAL PRIMARY KEY,
                job_description TEXT,
                resume_text TEXT,
                match_percentage FLOAT,
                missing_keywords TEXT,
                candidate_summary TEXT,
                experience TEXT
            );
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS applied_jobs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                job_id INTEGER REFERENCES jobs(id),
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, job_id)
            );
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS hr_messages (
                id SERIAL PRIMARY KEY,
                hr_id INTEGER REFERENCES users(id),
                candidate_id INTEGER REFERENCES users(id),
                job_id INTEGER REFERENCES jobs(id),
                message TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        cur.execute('''
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='users' AND column_name='registered_at'
                ) THEN
                    ALTER TABLE users ADD COLUMN registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                END IF;
            END $$;
        ''')

        cur.execute('''
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='users' AND column_name='is_approved'
                ) THEN
                    ALTER TABLE users ADD COLUMN is_approved BOOLEAN DEFAULT FALSE;
                END IF;
            END $$;
        ''')

    def _initialize_roles(self, cur):
        roles = ["Admin", "HR", "User"]
        for role in roles:
            cur.execute(
                'INSERT INTO roles (name) VALUES (%s) ON CONFLICT (name) DO NOTHING',
                (role,)
            )

    def _initialize_admin(self, cur):
        cur.execute('SELECT id FROM roles WHERE name = %s', ("Admin",))
        admin_role_id = cur.fetchone()
        if admin_role_id:
            admin_role_id = admin_role_id[0]
            cur.execute(
                '''
                INSERT INTO users (full_name, username, email, password, industry, role_id, company_name, is_approved)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (username) DO NOTHING
                ''',
                ("Super Admin", "admin", "admin@example.com", self._hash_password("admin123"), "Administration", admin_role_id, "Admin Company", True)
            )
        else:
            raise ValueError("Admin role not found during initialization.")

    @staticmethod
    def _hash_password(password):
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()