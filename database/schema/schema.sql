-- SkillBridge — PostgreSQL schema
-- ---------------------------------------------------------------------------
-- GENERATED FILE. Do not edit by hand.
--
-- Regenerate with:
--     cd backend && python ../database/schema/generate_schema.py
--
-- Alembic is the source of truth for schema *changes*; this file is a
-- flattened snapshot for reading, review and bootstrapping a database without
-- replaying the migration chain.
--
-- Tables: 79
-- ---------------------------------------------------------------------------

CREATE TABLE institutions (
	id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	slug VARCHAR(120) NOT NULL, 
	short_name VARCHAR(40), 
	institution_type VARCHAR(60) NOT NULL, 
	accreditation VARCHAR(120), 
	website VARCHAR(255), 
	logo_url VARCHAR(512), 
	description TEXT NOT NULL, 
	city VARCHAR(100), 
	state VARCHAR(100), 
	country VARCHAR(100) NOT NULL, 
	contact_email VARCHAR(255), 
	contact_phone VARCHAR(32), 
	established_year INTEGER, 
	verification_status VARCHAR(20) NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_institutions PRIMARY KEY (id)
);

CREATE INDEX ix_institutions_city ON institutions (city);

CREATE INDEX ix_institutions_deleted_at ON institutions (deleted_at);

CREATE UNIQUE INDEX ix_institutions_slug ON institutions (slug);

CREATE INDEX ix_institutions_created_at ON institutions (created_at);

CREATE INDEX ix_institutions_name ON institutions (name);

CREATE TABLE companies (
	id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	slug VARCHAR(120) NOT NULL, 
	industry_sector VARCHAR(80) NOT NULL, 
	website VARCHAR(255), 
	logo_url VARCHAR(512), 
	description TEXT NOT NULL, 
	about TEXT NOT NULL, 
	headquarters_city VARCHAR(100), 
	headquarters_country VARCHAR(100) NOT NULL, 
	locations JSONB NOT NULL, 
	employee_count INTEGER, 
	founded_year INTEGER, 
	contact_email VARCHAR(255), 
	contact_phone VARCHAR(32), 
	linkedin_url VARCHAR(255), 
	tech_stack JSONB NOT NULL, 
	benefits JSONB NOT NULL, 
	verification_status VARCHAR(20) NOT NULL, 
	is_hiring BOOLEAN NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_companies PRIMARY KEY (id), 
	CONSTRAINT ck_companies_employee_count_non_negative CHECK (employee_count is null or employee_count >= 0)
);

CREATE INDEX ix_companies_industry_sector ON companies (industry_sector);

CREATE INDEX ix_companies_headquarters_city ON companies (headquarters_city);

CREATE INDEX ix_companies_deleted_at ON companies (deleted_at);

CREATE UNIQUE INDEX ix_companies_slug ON companies (slug);

CREATE INDEX ix_companies_verification_status ON companies (verification_status);

CREATE INDEX ix_companies_name ON companies (name);

CREATE INDEX ix_companies_created_at ON companies (created_at);

CREATE TABLE skill_categories (
	id UUID NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	slug VARCHAR(120) NOT NULL, 
	description TEXT NOT NULL, 
	parent_id UUID, 
	icon VARCHAR(60), 
	color VARCHAR(20), 
	display_order INTEGER NOT NULL, 
	is_soft_skill BOOLEAN NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_skill_categories PRIMARY KEY (id), 
	CONSTRAINT fk_skill_categories_parent_id_skill_categories FOREIGN KEY(parent_id) REFERENCES skill_categories (id) ON DELETE SET NULL
);

CREATE INDEX ix_skill_categories_parent_id ON skill_categories (parent_id);

CREATE UNIQUE INDEX ix_skill_categories_slug ON skill_categories (slug);

CREATE INDEX ix_skill_categories_name ON skill_categories (name);

CREATE INDEX ix_skill_categories_created_at ON skill_categories (created_at);

CREATE TABLE job_roles (
	id UUID NOT NULL, 
	title VARCHAR(140) NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	family VARCHAR(80) NOT NULL, 
	description TEXT NOT NULL, 
	responsibilities JSONB NOT NULL, 
	typical_qualifications JSONB NOT NULL, 
	aliases JSONB NOT NULL, 
	seniority VARCHAR(30) NOT NULL, 
	avg_salary_min INTEGER, 
	avg_salary_max INTEGER, 
	demand_index FLOAT NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_job_roles PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_job_roles_slug ON job_roles (slug);

CREATE UNIQUE INDEX ix_job_roles_title ON job_roles (title);

CREATE INDEX ix_job_roles_created_at ON job_roles (created_at);

CREATE INDEX ix_job_roles_family ON job_roles (family);

CREATE TABLE permissions (
	id UUID NOT NULL, 
	code VARCHAR(80) NOT NULL, 
	resource VARCHAR(40) NOT NULL, 
	action VARCHAR(40) NOT NULL, 
	description VARCHAR(255) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_permissions PRIMARY KEY (id)
);

CREATE INDEX ix_permissions_resource ON permissions (resource);

CREATE INDEX ix_permissions_created_at ON permissions (created_at);

CREATE UNIQUE INDEX ix_permissions_code ON permissions (code);

CREATE TABLE roles (
	id UUID NOT NULL, 
	name VARCHAR(32) NOT NULL, 
	label VARCHAR(80) NOT NULL, 
	description VARCHAR(255) NOT NULL, 
	is_assignable_on_signup BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_roles PRIMARY KEY (id)
);

CREATE INDEX ix_roles_created_at ON roles (created_at);

CREATE UNIQUE INDEX ix_roles_name ON roles (name);

CREATE TABLE badges (
	id UUID NOT NULL, 
	code VARCHAR(40) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	description VARCHAR(400) NOT NULL, 
	icon VARCHAR(60) NOT NULL, 
	criteria VARCHAR(400) NOT NULL, 
	tier VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_badges PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_badges_code ON badges (code);

CREATE INDEX ix_badges_created_at ON badges (created_at);

CREATE TABLE departments (
	id UUID NOT NULL, 
	institution_id UUID NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	code VARCHAR(20) NOT NULL, 
	hod_name VARCHAR(160), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_departments PRIMARY KEY (id), 
	CONSTRAINT department_code_unique UNIQUE (institution_id, code), 
	CONSTRAINT fk_departments_institution_id_institutions FOREIGN KEY(institution_id) REFERENCES institutions (id) ON DELETE CASCADE
);

CREATE INDEX ix_departments_created_at ON departments (created_at);

CREATE INDEX ix_departments_institution_id ON departments (institution_id);

CREATE TABLE industry_partnerships (
	id UUID NOT NULL, 
	institution_id UUID NOT NULL, 
	company_id UUID NOT NULL, 
	partnership_type VARCHAR(60) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	summary TEXT NOT NULL, 
	started_on VARCHAR(20), 
	engagement_score INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_industry_partnerships PRIMARY KEY (id), 
	CONSTRAINT partnership_unique UNIQUE (institution_id, company_id, partnership_type), 
	CONSTRAINT fk_industry_partnerships_institution_id_institutions FOREIGN KEY(institution_id) REFERENCES institutions (id) ON DELETE CASCADE, 
	CONSTRAINT fk_industry_partnerships_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE CASCADE
);

CREATE INDEX ix_industry_partnerships_created_at ON industry_partnerships (created_at);

CREATE INDEX ix_industry_partnerships_company_id ON industry_partnerships (company_id);

CREATE INDEX ix_industry_partnerships_institution_id ON industry_partnerships (institution_id);

CREATE INDEX ix_industry_partnerships_status ON industry_partnerships (status);

CREATE TABLE skills (
	id UUID NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	slug VARCHAR(120) NOT NULL, 
	category_id UUID NOT NULL, 
	description TEXT NOT NULL, 
	aliases JSONB NOT NULL, 
	parent_skill_id UUID, 
	is_soft_skill BOOLEAN NOT NULL, 
	is_trending BOOLEAN NOT NULL, 
	demand_score FLOAT NOT NULL, 
	learning_resources JSONB NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_skills PRIMARY KEY (id), 
	CONSTRAINT fk_skills_category_id_skill_categories FOREIGN KEY(category_id) REFERENCES skill_categories (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_skills_parent_skill_id_skills FOREIGN KEY(parent_skill_id) REFERENCES skills (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX ix_skills_slug ON skills (slug);

CREATE INDEX ix_skills_is_soft_skill ON skills (is_soft_skill);

CREATE INDEX ix_skills_demand_score ON skills (demand_score);

CREATE INDEX ix_skills_category_active ON skills (category_id, is_active);

CREATE INDEX ix_skills_category_id ON skills (category_id);

CREATE UNIQUE INDEX ix_skills_name ON skills (name);

CREATE INDEX ix_skills_created_at ON skills (created_at);

CREATE TABLE role_permissions (
	role_id UUID NOT NULL, 
	permission_id UUID NOT NULL, 
	CONSTRAINT pk_role_permissions PRIMARY KEY (role_id, permission_id), 
	CONSTRAINT fk_role_permissions_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE, 
	CONSTRAINT fk_role_permissions_permission_id_permissions FOREIGN KEY(permission_id) REFERENCES permissions (id) ON DELETE CASCADE
);

CREATE TABLE users (
	id UUID NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	hashed_password VARCHAR(255) NOT NULL, 
	full_name VARCHAR(160) NOT NULL, 
	phone VARCHAR(32), 
	avatar_url VARCHAR(512), 
	status VARCHAR(32) NOT NULL, 
	is_email_verified BOOLEAN NOT NULL, 
	email_verified_at TIMESTAMP WITH TIME ZONE, 
	last_login_at TIMESTAMP WITH TIME ZONE, 
	last_login_ip VARCHAR(64), 
	failed_login_attempts INTEGER NOT NULL, 
	locked_until TIMESTAMP WITH TIME ZONE, 
	password_changed_at TIMESTAMP WITH TIME ZONE, 
	locale VARCHAR(10) NOT NULL, 
	timezone_name VARCHAR(64) NOT NULL, 
	institution_id UUID, 
	company_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_users PRIMARY KEY (id), 
	CONSTRAINT ck_users_email_min_length CHECK (length(email) >= 5), 
	CONSTRAINT ck_users_failed_attempts_non_negative CHECK (failed_login_attempts >= 0), 
	CONSTRAINT fk_users_institution_id_institutions FOREIGN KEY(institution_id) REFERENCES institutions (id) ON DELETE SET NULL, 
	CONSTRAINT fk_users_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX ix_users_email_lower ON users (lower(email));

CREATE INDEX ix_users_institution_id ON users (institution_id);

CREATE INDEX ix_users_deleted_at ON users (deleted_at);

CREATE INDEX ix_users_status ON users (status);

CREATE INDEX ix_users_company_id ON users (company_id);

CREATE INDEX ix_users_created_at ON users (created_at);

CREATE TABLE role_skills (
	id UUID NOT NULL, 
	job_role_id UUID NOT NULL, 
	skill_id UUID NOT NULL, 
	required_level VARCHAR(16) NOT NULL, 
	importance VARCHAR(16) NOT NULL, 
	weight FLOAT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_role_skills PRIMARY KEY (id), 
	CONSTRAINT role_skill_unique UNIQUE (job_role_id, skill_id), 
	CONSTRAINT ck_role_skills_role_skill_weight_positive CHECK (weight > 0), 
	CONSTRAINT fk_role_skills_job_role_id_job_roles FOREIGN KEY(job_role_id) REFERENCES job_roles (id) ON DELETE CASCADE, 
	CONSTRAINT fk_role_skills_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE CASCADE
);

CREATE INDEX ix_role_skills_job_role_id ON role_skills (job_role_id);

CREATE INDEX ix_role_skills_importance ON role_skills (importance);

CREATE INDEX ix_role_skills_created_at ON role_skills (created_at);

CREATE INDEX ix_role_skills_skill_id ON role_skills (skill_id);

CREATE TABLE opportunities (
	id UUID NOT NULL, 
	opportunity_type VARCHAR(28) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	slug VARCHAR(220) NOT NULL, 
	description TEXT NOT NULL, 
	responsibilities JSONB NOT NULL, 
	eligibility_text TEXT NOT NULL, 
	company_id UUID NOT NULL, 
	posted_by_id UUID, 
	job_role_id UUID, 
	status VARCHAR(20) NOT NULL, 
	work_mode VARCHAR(16) NOT NULL, 
	location_city VARCHAR(120), 
	location_country VARCHAR(100) NOT NULL, 
	positions INTEGER NOT NULL, 
	min_cgpa FLOAT, 
	max_backlogs INTEGER, 
	eligible_degrees JSONB NOT NULL, 
	eligible_graduation_years JSONB NOT NULL, 
	eligible_departments JSONB NOT NULL, 
	application_deadline TIMESTAMP WITH TIME ZONE, 
	starts_on DATE, 
	published_at TIMESTAMP WITH TIME ZONE, 
	closed_at TIMESTAMP WITH TIME ZONE, 
	views_count INTEGER NOT NULL, 
	applications_count INTEGER NOT NULL, 
	search_text TEXT NOT NULL, 
	extracted_requirements JSONB NOT NULL, 
	perks JSONB NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_opportunities PRIMARY KEY (id), 
	CONSTRAINT ck_opportunities_positions_positive CHECK (positions >= 1), 
	CONSTRAINT ck_opportunities_views_non_negative CHECK (views_count >= 0), 
	CONSTRAINT fk_opportunities_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE CASCADE, 
	CONSTRAINT fk_opportunities_posted_by_id_users FOREIGN KEY(posted_by_id) REFERENCES users (id) ON DELETE SET NULL, 
	CONSTRAINT fk_opportunities_job_role_id_job_roles FOREIGN KEY(job_role_id) REFERENCES job_roles (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX ix_opportunities_slug ON opportunities (slug);

CREATE INDEX ix_opportunities_company_id ON opportunities (company_id);

CREATE INDEX ix_opportunities_published_at ON opportunities (published_at);

CREATE INDEX ix_opportunities_created_at ON opportunities (created_at);

CREATE INDEX ix_opportunities_company_status ON opportunities (company_id, status);

CREATE INDEX ix_opportunities_title ON opportunities (title);

CREATE INDEX ix_opportunities_location_city ON opportunities (location_city);

CREATE INDEX ix_opportunities_status ON opportunities (status);

CREATE INDEX ix_opportunities_type_status ON opportunities (opportunity_type, status);

CREATE INDEX ix_opportunities_deadline ON opportunities (application_deadline);

CREATE INDEX ix_opportunities_opportunity_type ON opportunities (opportunity_type);

CREATE INDEX ix_opportunities_job_role_id ON opportunities (job_role_id);

CREATE INDEX ix_opportunities_posted_by_id ON opportunities (posted_by_id);

CREATE INDEX ix_opportunities_deleted_at ON opportunities (deleted_at);

CREATE TABLE student_profiles (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	institution_id UUID, 
	department_id UUID, 
	headline VARCHAR(160), 
	bio TEXT NOT NULL, 
	date_of_birth DATE, 
	gender VARCHAR(32), 
	city VARCHAR(100), 
	state VARCHAR(100), 
	country VARCHAR(100) NOT NULL, 
	enrollment_number VARCHAR(60), 
	degree VARCHAR(24) NOT NULL, 
	program_name VARCHAR(140), 
	current_year INTEGER, 
	current_semester INTEGER, 
	cgpa FLOAT, 
	graduation_year INTEGER, 
	backlogs INTEGER NOT NULL, 
	career_interests JSONB NOT NULL, 
	preferred_roles JSONB NOT NULL, 
	preferred_industries JSONB NOT NULL, 
	preferred_locations JSONB NOT NULL, 
	preferred_work_mode VARCHAR(16), 
	open_to_relocate BOOLEAN NOT NULL, 
	expected_stipend_min INTEGER, 
	expected_salary_min INTEGER, 
	target_job_role_id UUID, 
	portfolio_slug VARCHAR(120), 
	portfolio_visibility VARCHAR(24) NOT NULL, 
	profile_completion INTEGER NOT NULL, 
	skill_readiness_score FLOAT NOT NULL, 
	readiness_computed_at TIMESTAMP WITH TIME ZONE, 
	is_open_to_work BOOLEAN NOT NULL, 
	is_placed BOOLEAN NOT NULL, 
	placed_company_id UUID, 
	github_url VARCHAR(255), 
	linkedin_url VARCHAR(255), 
	portfolio_url VARCHAR(255), 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_student_profiles PRIMARY KEY (id), 
	CONSTRAINT ck_student_profiles_cgpa_range CHECK (cgpa is null or (cgpa >= 0 and cgpa <= 10)), 
	CONSTRAINT ck_student_profiles_year_range CHECK (current_year is null or (current_year between 1 and 6)), 
	CONSTRAINT ck_student_profiles_profile_completion_range CHECK (profile_completion between 0 and 100), 
	CONSTRAINT uq_student_profiles_user_id UNIQUE (user_id), 
	CONSTRAINT fk_student_profiles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT fk_student_profiles_institution_id_institutions FOREIGN KEY(institution_id) REFERENCES institutions (id) ON DELETE SET NULL, 
	CONSTRAINT fk_student_profiles_department_id_departments FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE SET NULL, 
	CONSTRAINT fk_student_profiles_target_job_role_id_job_roles FOREIGN KEY(target_job_role_id) REFERENCES job_roles (id) ON DELETE SET NULL, 
	CONSTRAINT fk_student_profiles_placed_company_id_companies FOREIGN KEY(placed_company_id) REFERENCES companies (id) ON DELETE SET NULL
);

CREATE INDEX ix_student_profiles_graduation_year ON student_profiles (graduation_year);

CREATE INDEX ix_student_profiles_created_at ON student_profiles (created_at);

CREATE INDEX ix_student_profiles_city ON student_profiles (city);

CREATE UNIQUE INDEX ix_student_profiles_portfolio_slug ON student_profiles (portfolio_slug);

CREATE INDEX ix_student_profiles_deleted_at ON student_profiles (deleted_at);

CREATE INDEX ix_student_profiles_institution_dept ON student_profiles (institution_id, department_id);

CREATE INDEX ix_student_profiles_institution_id ON student_profiles (institution_id);

CREATE INDEX ix_student_profiles_target_job_role_id ON student_profiles (target_job_role_id);

CREATE INDEX ix_student_profiles_is_placed ON student_profiles (is_placed);

CREATE INDEX ix_student_profiles_enrollment_number ON student_profiles (enrollment_number);

CREATE TABLE academician_profiles (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	institution_id UUID, 
	department_id UUID, 
	designation VARCHAR(120), 
	employee_code VARCHAR(60), 
	highest_qualification VARCHAR(120), 
	specialization VARCHAR(200), 
	teaching_experience_years INTEGER NOT NULL, 
	industry_experience_years INTEGER NOT NULL, 
	research_areas JSONB NOT NULL, 
	expertise_areas JSONB NOT NULL, 
	publications_count INTEGER NOT NULL, 
	patents_count INTEGER NOT NULL, 
	orcid_id VARCHAR(40), 
	google_scholar_url VARCHAR(255), 
	bio TEXT NOT NULL, 
	city VARCHAR(100), 
	is_available_for_mentorship BOOLEAN NOT NULL, 
	is_available_for_consultancy BOOLEAN NOT NULL, 
	profile_completion INTEGER NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_academician_profiles PRIMARY KEY (id), 
	CONSTRAINT uq_academician_profiles_user_id UNIQUE (user_id), 
	CONSTRAINT fk_academician_profiles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT fk_academician_profiles_institution_id_institutions FOREIGN KEY(institution_id) REFERENCES institutions (id) ON DELETE SET NULL, 
	CONSTRAINT fk_academician_profiles_department_id_departments FOREIGN KEY(department_id) REFERENCES departments (id) ON DELETE SET NULL
);

CREATE INDEX ix_academician_profiles_deleted_at ON academician_profiles (deleted_at);

CREATE INDEX ix_academician_profiles_institution_id ON academician_profiles (institution_id);

CREATE INDEX ix_academician_profiles_created_at ON academician_profiles (created_at);

CREATE TABLE recruiter_profiles (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	company_id UUID NOT NULL, 
	designation VARCHAR(120), 
	hiring_domains JSONB NOT NULL, 
	linkedin_url VARCHAR(255), 
	is_primary_contact BOOLEAN NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_recruiter_profiles PRIMARY KEY (id), 
	CONSTRAINT uq_recruiter_profiles_user_id UNIQUE (user_id), 
	CONSTRAINT fk_recruiter_profiles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT fk_recruiter_profiles_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE CASCADE
);

CREATE INDEX ix_recruiter_profiles_created_at ON recruiter_profiles (created_at);

CREATE INDEX ix_recruiter_profiles_company_id ON recruiter_profiles (company_id);

CREATE TABLE assessments (
	id UUID NOT NULL, 
	title VARCHAR(180) NOT NULL, 
	slug VARCHAR(180) NOT NULL, 
	description TEXT NOT NULL, 
	assessment_type VARCHAR(24) NOT NULL, 
	job_role_id UUID, 
	primary_skill_id UUID, 
	domain VARCHAR(80), 
	duration_minutes INTEGER NOT NULL, 
	passing_score FLOAT NOT NULL, 
	max_attempts INTEGER NOT NULL, 
	cooldown_hours INTEGER NOT NULL, 
	shuffle_questions BOOLEAN NOT NULL, 
	is_published BOOLEAN NOT NULL, 
	created_by_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_assessments PRIMARY KEY (id), 
	CONSTRAINT fk_assessments_job_role_id_job_roles FOREIGN KEY(job_role_id) REFERENCES job_roles (id) ON DELETE SET NULL, 
	CONSTRAINT fk_assessments_primary_skill_id_skills FOREIGN KEY(primary_skill_id) REFERENCES skills (id) ON DELETE SET NULL, 
	CONSTRAINT fk_assessments_created_by_id_users FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX ix_assessments_slug ON assessments (slug);

CREATE INDEX ix_assessments_primary_skill_id ON assessments (primary_skill_id);

CREATE INDEX ix_assessments_domain ON assessments (domain);

CREATE INDEX ix_assessments_assessment_type ON assessments (assessment_type);

CREATE INDEX ix_assessments_is_published ON assessments (is_published);

CREATE INDEX ix_assessments_title ON assessments (title);

CREATE INDEX ix_assessments_job_role_id ON assessments (job_role_id);

CREATE INDEX ix_assessments_created_at ON assessments (created_at);

CREATE TABLE audit_logs (
	id UUID NOT NULL, 
	actor_id UUID, 
	actor_email VARCHAR(255), 
	actor_roles JSONB NOT NULL, 
	action VARCHAR(40) NOT NULL, 
	resource_type VARCHAR(60), 
	resource_id UUID, 
	description VARCHAR(400) NOT NULL, 
	ip_address VARCHAR(64), 
	user_agent VARCHAR(300), 
	request_id VARCHAR(64), 
	status VARCHAR(20) NOT NULL, 
	meta JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_audit_logs PRIMARY KEY (id), 
	CONSTRAINT fk_audit_logs_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_audit_logs_request_id ON audit_logs (request_id);

CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);

CREATE INDEX ix_audit_logs_resource ON audit_logs (resource_type, resource_id);

CREATE INDEX ix_audit_logs_actor_id ON audit_logs (actor_id);

CREATE INDEX ix_audit_logs_action ON audit_logs (action);

CREATE INDEX ix_audit_logs_action_created ON audit_logs (action, created_at);

CREATE INDEX ix_audit_logs_actor_created ON audit_logs (actor_id, created_at);

CREATE TABLE saved_searches (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	name VARCHAR(140) NOT NULL, 
	entity VARCHAR(40) NOT NULL, 
	query VARCHAR(300) NOT NULL, 
	filters JSONB NOT NULL, 
	notify_on_new BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_saved_searches PRIMARY KEY (id), 
	CONSTRAINT fk_saved_searches_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_saved_searches_created_at ON saved_searches (created_at);

CREATE INDEX ix_saved_searches_user_id ON saved_searches (user_id);

CREATE TABLE documents (
	id UUID NOT NULL, 
	owner_id UUID NOT NULL, 
	document_type VARCHAR(32) NOT NULL, 
	title VARCHAR(220) NOT NULL, 
	original_filename VARCHAR(255) NOT NULL, 
	storage_key VARCHAR(400) NOT NULL, 
	storage_provider VARCHAR(20) NOT NULL, 
	content_type VARCHAR(120) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	checksum_sha256 VARCHAR(64), 
	visibility VARCHAR(24) NOT NULL, 
	scan_status VARCHAR(16) NOT NULL, 
	scan_detail VARCHAR(255), 
	is_primary_resume BOOLEAN NOT NULL, 
	extracted_text TEXT, 
	extraction_status VARCHAR(20) NOT NULL, 
	meta JSONB NOT NULL, 
	download_count INTEGER NOT NULL, 
	last_accessed_at TIMESTAMP WITH TIME ZONE, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_documents PRIMARY KEY (id), 
	CONSTRAINT ck_documents_document_size_positive CHECK (size_bytes > 0), 
	CONSTRAINT fk_documents_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT uq_documents_storage_key UNIQUE (storage_key)
);

CREATE INDEX ix_documents_checksum_sha256 ON documents (checksum_sha256);

CREATE INDEX ix_documents_created_at ON documents (created_at);

CREATE INDEX ix_documents_owner_type ON documents (owner_id, document_type);

CREATE INDEX ix_documents_owner_id ON documents (owner_id);

CREATE INDEX ix_documents_document_type ON documents (document_type);

CREATE INDEX ix_documents_deleted_at ON documents (deleted_at);

CREATE INDEX ix_documents_scan_status ON documents (scan_status);

CREATE TABLE events (
	id UUID NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	slug VARCHAR(220) NOT NULL, 
	description TEXT NOT NULL, 
	event_type VARCHAR(28) NOT NULL, 
	host_company_id UUID, 
	host_institution_id UUID, 
	created_by_id UUID, 
	speaker_name VARCHAR(160), 
	speaker_designation VARCHAR(160), 
	mode VARCHAR(16) NOT NULL, 
	venue VARCHAR(300), 
	meeting_link VARCHAR(500), 
	starts_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	ends_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	registration_deadline TIMESTAMP WITH TIME ZONE, 
	capacity INTEGER, 
	registered_count INTEGER NOT NULL, 
	skill_tags JSONB NOT NULL, 
	target_audience JSONB NOT NULL, 
	grants_certificate BOOLEAN NOT NULL, 
	banner_url VARCHAR(500), 
	search_text TEXT NOT NULL, 
	is_published BOOLEAN NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_events PRIMARY KEY (id), 
	CONSTRAINT ck_events_event_time_order CHECK (ends_at > starts_at), 
	CONSTRAINT ck_events_event_capacity_positive CHECK (capacity is null or capacity > 0), 
	CONSTRAINT fk_events_host_company_id_companies FOREIGN KEY(host_company_id) REFERENCES companies (id) ON DELETE SET NULL, 
	CONSTRAINT fk_events_host_institution_id_institutions FOREIGN KEY(host_institution_id) REFERENCES institutions (id) ON DELETE SET NULL, 
	CONSTRAINT fk_events_created_by_id_users FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_events_starts_published ON events (starts_at, is_published);

CREATE UNIQUE INDEX ix_events_slug ON events (slug);

CREATE INDEX ix_events_starts_at ON events (starts_at);

CREATE INDEX ix_events_created_at ON events (created_at);

CREATE INDEX ix_events_event_type ON events (event_type);

CREATE INDEX ix_events_is_published ON events (is_published);

CREATE INDEX ix_events_host_institution_id ON events (host_institution_id);

CREATE INDEX ix_events_title ON events (title);

CREATE INDEX ix_events_host_company_id ON events (host_company_id);

CREATE INDEX ix_events_deleted_at ON events (deleted_at);

CREATE TABLE learning_programs (
	id UUID NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	slug VARCHAR(220) NOT NULL, 
	summary VARCHAR(400) NOT NULL, 
	description TEXT NOT NULL, 
	program_type VARCHAR(28) NOT NULL, 
	provider_company_id UUID, 
	provider_name VARCHAR(180), 
	created_by_id UUID, 
	difficulty VARCHAR(12) NOT NULL, 
	duration_hours INTEGER NOT NULL, 
	mode VARCHAR(16) NOT NULL, 
	price_amount INTEGER NOT NULL, 
	currency VARCHAR(8) NOT NULL, 
	is_free BOOLEAN NOT NULL, 
	external_url VARCHAR(500), 
	thumbnail_url VARCHAR(500), 
	starts_on DATE, 
	ends_on DATE, 
	seats INTEGER, 
	grants_certificate BOOLEAN NOT NULL, 
	outcomes JSONB NOT NULL, 
	prerequisites JSONB NOT NULL, 
	rating FLOAT NOT NULL, 
	enrollment_count INTEGER NOT NULL, 
	search_text TEXT NOT NULL, 
	is_published BOOLEAN NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_learning_programs PRIMARY KEY (id), 
	CONSTRAINT fk_learning_programs_provider_company_id_companies FOREIGN KEY(provider_company_id) REFERENCES companies (id) ON DELETE SET NULL, 
	CONSTRAINT fk_learning_programs_created_by_id_users FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_learning_programs_deleted_at ON learning_programs (deleted_at);

CREATE INDEX ix_learning_programs_type_published ON learning_programs (program_type, is_published);

CREATE INDEX ix_learning_programs_is_published ON learning_programs (is_published);

CREATE INDEX ix_learning_programs_is_free ON learning_programs (is_free);

CREATE INDEX ix_learning_programs_program_type ON learning_programs (program_type);

CREATE INDEX ix_learning_programs_provider_company_id ON learning_programs (provider_company_id);

CREATE INDEX ix_learning_programs_title ON learning_programs (title);

CREATE UNIQUE INDEX ix_learning_programs_slug ON learning_programs (slug);

CREATE INDEX ix_learning_programs_created_at ON learning_programs (created_at);

CREATE TABLE user_roles (
	user_id UUID NOT NULL, 
	role_id UUID NOT NULL, 
	granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT pk_user_roles PRIMARY KEY (user_id, role_id), 
	CONSTRAINT fk_user_roles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT fk_user_roles_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE
);

CREATE TABLE user_sessions (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	refresh_token_hash VARCHAR(128) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	revoked_reason VARCHAR(80), 
	rotated_from UUID, 
	user_agent VARCHAR(255), 
	ip_address VARCHAR(64), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_user_sessions PRIMARY KEY (id), 
	CONSTRAINT fk_user_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_user_sessions_user_id ON user_sessions (user_id);

CREATE INDEX ix_user_sessions_user_active ON user_sessions (user_id, revoked_at);

CREATE INDEX ix_user_sessions_refresh_token_hash ON user_sessions (refresh_token_hash);

CREATE INDEX ix_user_sessions_created_at ON user_sessions (created_at);

CREATE TABLE one_time_tokens (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	token_hash VARCHAR(128) NOT NULL, 
	purpose VARCHAR(32) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	used_at TIMESTAMP WITH TIME ZONE, 
	meta JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_one_time_tokens PRIMARY KEY (id), 
	CONSTRAINT token_hash_unique UNIQUE (token_hash), 
	CONSTRAINT fk_one_time_tokens_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_one_time_tokens_created_at ON one_time_tokens (created_at);

CREATE INDEX ix_one_time_tokens_user_purpose ON one_time_tokens (user_id, purpose);

CREATE TABLE mentors (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	company_id UUID, 
	institution_id UUID, 
	headline VARCHAR(200) NOT NULL, 
	bio TEXT NOT NULL, 
	designation VARCHAR(140), 
	experience_years INTEGER NOT NULL, 
	industry VARCHAR(100), 
	expertise_skill_ids JSONB NOT NULL, 
	topics JSONB NOT NULL, 
	languages JSONB NOT NULL, 
	availability JSONB NOT NULL, 
	capacity_per_month INTEGER NOT NULL, 
	session_duration_minutes INTEGER NOT NULL, 
	is_accepting_requests BOOLEAN NOT NULL, 
	rating FLOAT NOT NULL, 
	sessions_completed INTEGER NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_mentors PRIMARY KEY (id), 
	CONSTRAINT ck_mentors_mentor_capacity_non_negative CHECK (capacity_per_month >= 0), 
	CONSTRAINT uq_mentors_user_id UNIQUE (user_id), 
	CONSTRAINT fk_mentors_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT fk_mentors_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE SET NULL, 
	CONSTRAINT fk_mentors_institution_id_institutions FOREIGN KEY(institution_id) REFERENCES institutions (id) ON DELETE SET NULL
);

CREATE INDEX ix_mentors_created_at ON mentors (created_at);

CREATE INDEX ix_mentors_industry ON mentors (industry);

CREATE INDEX ix_mentors_institution_id ON mentors (institution_id);

CREATE INDEX ix_mentors_company_id ON mentors (company_id);

CREATE INDEX ix_mentors_is_accepting_requests ON mentors (is_accepting_requests);

CREATE TABLE conversations (
	id UUID NOT NULL, 
	subject VARCHAR(220) NOT NULL, 
	context_type VARCHAR(40) NOT NULL, 
	context_id UUID, 
	created_by_id UUID, 
	last_message_at TIMESTAMP WITH TIME ZONE, 
	is_closed BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_conversations PRIMARY KEY (id), 
	CONSTRAINT fk_conversations_created_by_id_users FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_conversations_created_at ON conversations (created_at);

CREATE INDEX ix_conversations_context ON conversations (context_type, context_id);

CREATE INDEX ix_conversations_last_message_at ON conversations (last_message_at);

CREATE TABLE notifications (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	category VARCHAR(24) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	body TEXT NOT NULL, 
	action_url VARCHAR(400), 
	action_label VARCHAR(80), 
	icon VARCHAR(40), 
	resource_type VARCHAR(60), 
	resource_id UUID, 
	read_at TIMESTAMP WITH TIME ZONE, 
	emailed_at TIMESTAMP WITH TIME ZONE, 
	meta JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_notifications PRIMARY KEY (id), 
	CONSTRAINT fk_notifications_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_notifications_user_read ON notifications (user_id, read_at);

CREATE INDEX ix_notifications_user_id ON notifications (user_id);

CREATE INDEX ix_notifications_user_created ON notifications (user_id, created_at);

CREATE INDEX ix_notifications_resource_id ON notifications (resource_id);

CREATE INDEX ix_notifications_created_at ON notifications (created_at);

CREATE INDEX ix_notifications_category ON notifications (category);

CREATE TABLE notification_preferences (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	category VARCHAR(24) NOT NULL, 
	channel VARCHAR(16) NOT NULL, 
	is_enabled BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_notification_preferences PRIMARY KEY (id), 
	CONSTRAINT notification_preference_unique UNIQUE (user_id, category, channel), 
	CONSTRAINT fk_notification_preferences_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_notification_preferences_user_id ON notification_preferences (user_id);

CREATE INDEX ix_notification_preferences_created_at ON notification_preferences (created_at);

CREATE TABLE email_logs (
	id UUID NOT NULL, 
	to_email VARCHAR(255) NOT NULL, 
	template VARCHAR(80) NOT NULL, 
	subject VARCHAR(300) NOT NULL, 
	provider VARCHAR(30) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	error TEXT, 
	sent_at TIMESTAMP WITH TIME ZONE, 
	user_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_email_logs PRIMARY KEY (id), 
	CONSTRAINT fk_email_logs_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_email_logs_status ON email_logs (status);

CREATE INDEX ix_email_logs_template ON email_logs (template);

CREATE INDEX ix_email_logs_to_email ON email_logs (to_email);

CREATE INDEX ix_email_logs_created_at ON email_logs (created_at);

CREATE TABLE recommendations (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	recommendation_type VARCHAR(32) NOT NULL, 
	target_id UUID NOT NULL, 
	target_title VARCHAR(250) NOT NULL, 
	match_score FLOAT NOT NULL, 
	breakdown JSONB NOT NULL, 
	matching_skills JSONB NOT NULL, 
	missing_skills JSONB NOT NULL, 
	reasons JSONB NOT NULL, 
	reason_summary TEXT NOT NULL, 
	next_steps JSONB NOT NULL, 
	generated_by VARCHAR(32) NOT NULL, 
	computed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	is_dismissed BOOLEAN NOT NULL, 
	clicked_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_recommendations PRIMARY KEY (id), 
	CONSTRAINT recommendation_unique UNIQUE (user_id, recommendation_type, target_id), 
	CONSTRAINT ck_recommendations_recommendation_score_range CHECK (match_score between 0 and 100), 
	CONSTRAINT fk_recommendations_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_recommendations_recommendation_type ON recommendations (recommendation_type);

CREATE INDEX ix_recommendations_expires_at ON recommendations (expires_at);

CREATE INDEX ix_recommendations_user_type_score ON recommendations (user_id, recommendation_type, match_score);

CREATE INDEX ix_recommendations_target_id ON recommendations (target_id);

CREATE INDEX ix_recommendations_user_id ON recommendations (user_id);

CREATE INDEX ix_recommendations_created_at ON recommendations (created_at);

CREATE TABLE student_skills (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	skill_id UUID NOT NULL, 
	level VARCHAR(16) NOT NULL, 
	score FLOAT NOT NULL, 
	confidence FLOAT NOT NULL, 
	source VARCHAR(24) NOT NULL, 
	evidence JSONB NOT NULL, 
	years_of_experience FLOAT, 
	last_assessed_at TIMESTAMP WITH TIME ZONE, 
	endorsement_count INTEGER NOT NULL, 
	is_verified BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_student_skills PRIMARY KEY (id), 
	CONSTRAINT student_skill_unique UNIQUE (student_id, skill_id), 
	CONSTRAINT ck_student_skills_student_skill_score_range CHECK (score between 0 and 100), 
	CONSTRAINT ck_student_skills_student_skill_confidence_range CHECK (confidence between 0 and 1), 
	CONSTRAINT fk_student_skills_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE, 
	CONSTRAINT fk_student_skills_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE CASCADE
);

CREATE INDEX ix_student_skills_created_at ON student_skills (created_at);

CREATE INDEX ix_student_skills_source ON student_skills (source);

CREATE INDEX ix_student_skills_skill_level ON student_skills (skill_id, level);

CREATE INDEX ix_student_skills_student_id ON student_skills (student_id);

CREATE INDEX ix_student_skills_skill_id ON student_skills (skill_id);

CREATE TABLE skill_gap_analyses (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	job_role_id UUID NOT NULL, 
	readiness_score FLOAT NOT NULL, 
	gap_percentage FLOAT NOT NULL, 
	matched_count INTEGER NOT NULL, 
	total_required INTEGER NOT NULL, 
	summary TEXT NOT NULL, 
	computed_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_skill_gap_analyses PRIMARY KEY (id), 
	CONSTRAINT skill_gap_unique UNIQUE (student_id, job_role_id), 
	CONSTRAINT ck_skill_gap_analyses_gap_readiness_range CHECK (readiness_score between 0 and 100), 
	CONSTRAINT fk_skill_gap_analyses_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE, 
	CONSTRAINT fk_skill_gap_analyses_job_role_id_job_roles FOREIGN KEY(job_role_id) REFERENCES job_roles (id) ON DELETE CASCADE
);

CREATE INDEX ix_skill_gap_analyses_created_at ON skill_gap_analyses (created_at);

CREATE INDEX ix_skill_gap_analyses_student_id ON skill_gap_analyses (student_id);

CREATE INDEX ix_skill_gap_analyses_computed_at ON skill_gap_analyses (computed_at);

CREATE INDEX ix_skill_gap_analyses_job_role_id ON skill_gap_analyses (job_role_id);

CREATE TABLE opportunity_skills (
	id UUID NOT NULL, 
	opportunity_id UUID NOT NULL, 
	skill_id UUID NOT NULL, 
	required_level VARCHAR(16) NOT NULL, 
	importance VARCHAR(16) NOT NULL, 
	weight FLOAT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_opportunity_skills PRIMARY KEY (id), 
	CONSTRAINT opportunity_skill_unique UNIQUE (opportunity_id, skill_id), 
	CONSTRAINT ck_opportunity_skills_opportunity_skill_weight_positive CHECK (weight > 0), 
	CONSTRAINT fk_opportunity_skills_opportunity_id_opportunities FOREIGN KEY(opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE, 
	CONSTRAINT fk_opportunity_skills_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE CASCADE
);

CREATE INDEX ix_opportunity_skills_skill_id ON opportunity_skills (skill_id);

CREATE INDEX ix_opportunity_skills_opportunity_id ON opportunity_skills (opportunity_id);

CREATE INDEX ix_opportunity_skills_importance ON opportunity_skills (importance);

CREATE INDEX ix_opportunity_skills_created_at ON opportunity_skills (created_at);

CREATE TABLE internships (
	id UUID NOT NULL, 
	duration_weeks INTEGER NOT NULL, 
	stipend_min INTEGER, 
	stipend_max INTEGER, 
	stipend_currency VARCHAR(8) NOT NULL, 
	is_paid BOOLEAN NOT NULL, 
	learning_outcomes JSONB NOT NULL, 
	mentor_name VARCHAR(160), 
	is_ppo_available BOOLEAN NOT NULL, 
	certificate_provided BOOLEAN NOT NULL, 
	CONSTRAINT pk_internships PRIMARY KEY (id), 
	CONSTRAINT ck_internships_stipend_range_order CHECK (stipend_max is null or stipend_min is null or stipend_max >= stipend_min), 
	CONSTRAINT ck_internships_duration_range CHECK (duration_weeks between 1 and 104), 
	CONSTRAINT fk_internships_id_opportunities FOREIGN KEY(id) REFERENCES opportunities (id) ON DELETE CASCADE
);

CREATE TABLE jobs (
	id UUID NOT NULL, 
	employment_type VARCHAR(20) NOT NULL, 
	salary_min INTEGER, 
	salary_max INTEGER, 
	salary_currency VARCHAR(8) NOT NULL, 
	salary_period VARCHAR(16) NOT NULL, 
	experience_min_years FLOAT NOT NULL, 
	experience_max_years FLOAT, 
	notice_period_days INTEGER, 
	bond_months INTEGER, 
	hiring_process JSONB NOT NULL, 
	CONSTRAINT pk_jobs PRIMARY KEY (id), 
	CONSTRAINT ck_jobs_salary_range_order CHECK (salary_max is null or salary_min is null or salary_max >= salary_min), 
	CONSTRAINT ck_jobs_experience_non_negative CHECK (experience_min_years >= 0), 
	CONSTRAINT fk_jobs_id_opportunities FOREIGN KEY(id) REFERENCES opportunities (id) ON DELETE CASCADE
);

CREATE TABLE live_projects (
	id UUID NOT NULL, 
	problem_statement TEXT NOT NULL, 
	expected_outcome TEXT NOT NULL, 
	team_size_min INTEGER NOT NULL, 
	team_size_max INTEGER NOT NULL, 
	timeline_weeks INTEGER NOT NULL, 
	stipend_amount INTEGER, 
	mentor_user_id UUID, 
	allows_team_application BOOLEAN NOT NULL, 
	CONSTRAINT pk_live_projects PRIMARY KEY (id), 
	CONSTRAINT ck_live_projects_team_size_order CHECK (team_size_max >= team_size_min), 
	CONSTRAINT fk_live_projects_id_opportunities FOREIGN KEY(id) REFERENCES opportunities (id) ON DELETE CASCADE, 
	CONSTRAINT fk_live_projects_mentor_user_id_users FOREIGN KEY(mentor_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE faculty_opportunities (
	id UUID NOT NULL, 
	kind VARCHAR(32) NOT NULL, 
	duration_days INTEGER, 
	honorarium INTEGER, 
	min_teaching_experience_years INTEGER NOT NULL, 
	focus_areas JSONB NOT NULL, 
	certification_provided BOOLEAN NOT NULL, 
	seats INTEGER, 
	CONSTRAINT pk_faculty_opportunities PRIMARY KEY (id), 
	CONSTRAINT fk_faculty_opportunities_id_opportunities FOREIGN KEY(id) REFERENCES opportunities (id) ON DELETE CASCADE
);

CREATE INDEX ix_faculty_opportunities_kind ON faculty_opportunities (kind);

CREATE TABLE saved_opportunities (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	opportunity_id UUID NOT NULL, 
	note VARCHAR(400) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_saved_opportunities PRIMARY KEY (id), 
	CONSTRAINT saved_opportunity_unique UNIQUE (user_id, opportunity_id), 
	CONSTRAINT fk_saved_opportunities_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT fk_saved_opportunities_opportunity_id_opportunities FOREIGN KEY(opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE
);

CREATE INDEX ix_saved_opportunities_opportunity_id ON saved_opportunities (opportunity_id);

CREATE INDEX ix_saved_opportunities_created_at ON saved_opportunities (created_at);

CREATE INDEX ix_saved_opportunities_user_id ON saved_opportunities (user_id);

CREATE TABLE education_records (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	level VARCHAR(24) NOT NULL, 
	institution_name VARCHAR(200) NOT NULL, 
	board_or_university VARCHAR(200), 
	program VARCHAR(160), 
	specialization VARCHAR(160), 
	start_year INTEGER NOT NULL, 
	end_year INTEGER, 
	score_value FLOAT, 
	score_type VARCHAR(20) NOT NULL, 
	is_verified BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_education_records PRIMARY KEY (id), 
	CONSTRAINT ck_education_records_education_year_order CHECK (end_year is null or end_year >= start_year), 
	CONSTRAINT fk_education_records_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE
);

CREATE INDEX ix_education_records_student_id ON education_records (student_id);

CREATE INDEX ix_education_records_created_at ON education_records (created_at);

CREATE TABLE experience_records (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	kind VARCHAR(40) NOT NULL, 
	title VARCHAR(180) NOT NULL, 
	organization VARCHAR(180) NOT NULL, 
	location VARCHAR(120), 
	work_mode VARCHAR(16), 
	description TEXT NOT NULL, 
	start_date DATE, 
	end_date DATE, 
	is_current BOOLEAN NOT NULL, 
	skill_tags JSONB NOT NULL, 
	source_application_id UUID, 
	is_verified BOOLEAN NOT NULL, 
	verified_by_company_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_experience_records PRIMARY KEY (id), 
	CONSTRAINT fk_experience_records_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE, 
	CONSTRAINT fk_experience_records_verified_by_company_id_companies FOREIGN KEY(verified_by_company_id) REFERENCES companies (id) ON DELETE SET NULL
);

CREATE INDEX ix_experience_records_created_at ON experience_records (created_at);

CREATE INDEX ix_experience_records_kind ON experience_records (kind);

CREATE INDEX ix_experience_records_student_id ON experience_records (student_id);

CREATE INDEX ix_experience_records_source_application_id ON experience_records (source_application_id);

CREATE TABLE student_projects (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	title VARCHAR(180) NOT NULL, 
	description TEXT NOT NULL, 
	role VARCHAR(120), 
	team_size INTEGER NOT NULL, 
	skill_tags JSONB NOT NULL, 
	repository_url VARCHAR(255), 
	demo_url VARCHAR(255), 
	start_date DATE, 
	end_date DATE, 
	highlights JSONB NOT NULL, 
	is_featured BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_student_projects PRIMARY KEY (id), 
	CONSTRAINT fk_student_projects_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE
);

CREATE INDEX ix_student_projects_student_id ON student_projects (student_id);

CREATE INDEX ix_student_projects_created_at ON student_projects (created_at);

CREATE TABLE achievements (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	category VARCHAR(40) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	issuer VARCHAR(180), 
	achieved_on DATE, 
	position VARCHAR(60), 
	url VARCHAR(255), 
	is_verified BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_achievements PRIMARY KEY (id), 
	CONSTRAINT fk_achievements_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE
);

CREATE INDEX ix_achievements_created_at ON achievements (created_at);

CREATE INDEX ix_achievements_student_id ON achievements (student_id);

CREATE INDEX ix_achievements_category ON achievements (category);

CREATE TABLE applications (
	id UUID NOT NULL, 
	opportunity_id UUID NOT NULL, 
	student_id UUID, 
	academician_id UUID, 
	status VARCHAR(20) NOT NULL, 
	cover_letter TEXT NOT NULL, 
	resume_document_id UUID, 
	answers JSONB NOT NULL, 
	match_score FLOAT NOT NULL, 
	match_breakdown JSONB NOT NULL, 
	matching_skills JSONB NOT NULL, 
	missing_skills JSONB NOT NULL, 
	recruiter_rating INTEGER, 
	recruiter_notes TEXT NOT NULL, 
	rejection_reason VARCHAR(400), 
	withdrawn_reason VARCHAR(400), 
	submitted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	last_status_change_at TIMESTAMP WITH TIME ZONE, 
	decided_at TIMESTAMP WITH TIME ZONE, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_applications PRIMARY KEY (id), 
	CONSTRAINT application_unique UNIQUE (opportunity_id, student_id), 
	CONSTRAINT faculty_application_unique UNIQUE (opportunity_id, academician_id), 
	CONSTRAINT ck_applications_one_applicant_identity CHECK ((student_id is not null and academician_id is null) or (student_id is null and academician_id is not null)), 
	CONSTRAINT ck_applications_match_score_range CHECK (match_score between 0 and 100), 
	CONSTRAINT fk_applications_opportunity_id_opportunities FOREIGN KEY(opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE, 
	CONSTRAINT fk_applications_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE, 
	CONSTRAINT fk_applications_academician_id_academician_profiles FOREIGN KEY(academician_id) REFERENCES academician_profiles (id) ON DELETE CASCADE, 
	CONSTRAINT fk_applications_resume_document_id_documents FOREIGN KEY(resume_document_id) REFERENCES documents (id) ON DELETE SET NULL
);

CREATE INDEX ix_applications_opportunity_id ON applications (opportunity_id);

CREATE INDEX ix_applications_student_id ON applications (student_id);

CREATE INDEX ix_applications_student_status ON applications (student_id, status);

CREATE INDEX ix_applications_created_at ON applications (created_at);

CREATE INDEX ix_applications_match_score ON applications (match_score);

CREATE INDEX ix_applications_academician_id ON applications (academician_id);

CREATE INDEX ix_applications_status ON applications (status);

CREATE INDEX ix_applications_status_created ON applications (status, created_at);

CREATE TABLE assessment_questions (
	id UUID NOT NULL, 
	assessment_id UUID NOT NULL, 
	skill_id UUID NOT NULL, 
	subskill VARCHAR(120), 
	question_type VARCHAR(24) NOT NULL, 
	prompt TEXT NOT NULL, 
	code_snippet TEXT, 
	difficulty VARCHAR(12) NOT NULL, 
	weight FLOAT NOT NULL, 
	explanation TEXT NOT NULL, 
	display_order INTEGER NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_assessment_questions PRIMARY KEY (id), 
	CONSTRAINT ck_assessment_questions_question_weight_positive CHECK (weight > 0), 
	CONSTRAINT fk_assessment_questions_assessment_id_assessments FOREIGN KEY(assessment_id) REFERENCES assessments (id) ON DELETE CASCADE, 
	CONSTRAINT fk_assessment_questions_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE RESTRICT
);

CREATE INDEX ix_assessment_questions_created_at ON assessment_questions (created_at);

CREATE INDEX ix_assessment_questions_skill_id ON assessment_questions (skill_id);

CREATE INDEX ix_assessment_questions_assessment_id ON assessment_questions (assessment_id);

CREATE INDEX ix_assessment_questions_assessment_order ON assessment_questions (assessment_id, display_order);

CREATE INDEX ix_assessment_questions_difficulty ON assessment_questions (difficulty);

CREATE TABLE assessment_attempts (
	id UUID NOT NULL, 
	assessment_id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	attempt_number INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	submitted_at TIMESTAMP WITH TIME ZONE, 
	duration_seconds INTEGER, 
	raw_score FLOAT NOT NULL, 
	max_score FLOAT NOT NULL, 
	percentage FLOAT NOT NULL, 
	confidence FLOAT NOT NULL, 
	is_passed BOOLEAN NOT NULL, 
	question_order JSONB NOT NULL, 
	feedback TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_assessment_attempts PRIMARY KEY (id), 
	CONSTRAINT ck_assessment_attempts_attempt_percentage_range CHECK (percentage between 0 and 100), 
	CONSTRAINT fk_assessment_attempts_assessment_id_assessments FOREIGN KEY(assessment_id) REFERENCES assessments (id) ON DELETE CASCADE, 
	CONSTRAINT fk_assessment_attempts_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE
);

CREATE INDEX ix_attempts_student_assessment ON assessment_attempts (student_id, assessment_id);

CREATE INDEX ix_assessment_attempts_status ON assessment_attempts (status);

CREATE INDEX ix_assessment_attempts_student_id ON assessment_attempts (student_id);

CREATE INDEX ix_assessment_attempts_created_at ON assessment_attempts (created_at);

CREATE INDEX ix_assessment_attempts_assessment_id ON assessment_attempts (assessment_id);

CREATE TABLE document_access_grants (
	id UUID NOT NULL, 
	document_id UUID NOT NULL, 
	granted_to_user_id UUID NOT NULL, 
	granted_by_user_id UUID, 
	reason VARCHAR(200) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_document_access_grants PRIMARY KEY (id), 
	CONSTRAINT fk_document_access_grants_document_id_documents FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE, 
	CONSTRAINT fk_document_access_grants_granted_to_user_id_users FOREIGN KEY(granted_to_user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT fk_document_access_grants_granted_by_user_id_users FOREIGN KEY(granted_by_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_document_access_grants_document_id ON document_access_grants (document_id);

CREATE INDEX ix_document_access_grants_granted_to_user_id ON document_access_grants (granted_to_user_id);

CREATE INDEX ix_document_access_grants_created_at ON document_access_grants (created_at);

CREATE TABLE event_registrations (
	id UUID NOT NULL, 
	event_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	attended_at TIMESTAMP WITH TIME ZONE, 
	certificate_issued BOOLEAN NOT NULL, 
	certificate_code VARCHAR(60), 
	feedback_rating INTEGER, 
	feedback_comment TEXT NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_event_registrations PRIMARY KEY (id), 
	CONSTRAINT event_registration_unique UNIQUE (event_id, user_id), 
	CONSTRAINT fk_event_registrations_event_id_events FOREIGN KEY(event_id) REFERENCES events (id) ON DELETE CASCADE, 
	CONSTRAINT fk_event_registrations_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT uq_event_registrations_certificate_code UNIQUE (certificate_code)
);

CREATE INDEX ix_event_registrations_user_id ON event_registrations (user_id);

CREATE INDEX ix_event_registrations_status ON event_registrations (status);

CREATE INDEX ix_event_registrations_created_at ON event_registrations (created_at);

CREATE INDEX ix_event_registrations_event_id ON event_registrations (event_id);

CREATE TABLE program_skills (
	id UUID NOT NULL, 
	program_id UUID NOT NULL, 
	skill_id UUID NOT NULL, 
	target_level VARCHAR(16) NOT NULL, 
	coverage_weight FLOAT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_program_skills PRIMARY KEY (id), 
	CONSTRAINT program_skill_unique UNIQUE (program_id, skill_id), 
	CONSTRAINT fk_program_skills_program_id_learning_programs FOREIGN KEY(program_id) REFERENCES learning_programs (id) ON DELETE CASCADE, 
	CONSTRAINT fk_program_skills_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE CASCADE
);

CREATE INDEX ix_program_skills_created_at ON program_skills (created_at);

CREATE INDEX ix_program_skills_skill_id ON program_skills (skill_id);

CREATE INDEX ix_program_skills_program_id ON program_skills (program_id);

CREATE TABLE course_modules (
	id UUID NOT NULL, 
	program_id UUID NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	content_type VARCHAR(20) NOT NULL, 
	content_url VARCHAR(500), 
	duration_minutes INTEGER NOT NULL, 
	display_order INTEGER NOT NULL, 
	is_mandatory BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_course_modules PRIMARY KEY (id), 
	CONSTRAINT fk_course_modules_program_id_learning_programs FOREIGN KEY(program_id) REFERENCES learning_programs (id) ON DELETE CASCADE
);

CREATE INDEX ix_course_modules_program_id ON course_modules (program_id);

CREATE INDEX ix_course_modules_program_order ON course_modules (program_id, display_order);

CREATE INDEX ix_course_modules_created_at ON course_modules (created_at);

CREATE TABLE enrollments (
	id UUID NOT NULL, 
	program_id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	progress_percentage FLOAT NOT NULL, 
	enrolled_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	last_activity_at TIMESTAMP WITH TIME ZONE, 
	final_score FLOAT, 
	recommended_for_role_id UUID, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_enrollments PRIMARY KEY (id), 
	CONSTRAINT enrollment_unique UNIQUE (program_id, student_id), 
	CONSTRAINT ck_enrollments_progress_range CHECK (progress_percentage between 0 and 100), 
	CONSTRAINT fk_enrollments_program_id_learning_programs FOREIGN KEY(program_id) REFERENCES learning_programs (id) ON DELETE CASCADE, 
	CONSTRAINT fk_enrollments_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE
);

CREATE INDEX ix_enrollments_status ON enrollments (status);

CREATE INDEX ix_enrollments_student_id ON enrollments (student_id);

CREATE INDEX ix_enrollments_created_at ON enrollments (created_at);

CREATE INDEX ix_enrollments_program_id ON enrollments (program_id);

CREATE TABLE certifications (
	id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	slug VARCHAR(220) NOT NULL, 
	issuer VARCHAR(180) NOT NULL, 
	description TEXT NOT NULL, 
	program_id UUID, 
	validity_months INTEGER, 
	skill_ids JSONB NOT NULL, 
	external_url VARCHAR(500), 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_certifications PRIMARY KEY (id), 
	CONSTRAINT fk_certifications_program_id_learning_programs FOREIGN KEY(program_id) REFERENCES learning_programs (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX ix_certifications_slug ON certifications (slug);

CREATE INDEX ix_certifications_created_at ON certifications (created_at);

CREATE INDEX ix_certifications_name ON certifications (name);

CREATE INDEX ix_certifications_issuer ON certifications (issuer);

CREATE TABLE learning_paths (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	job_role_id UUID NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	summary TEXT NOT NULL, 
	estimated_weeks INTEGER NOT NULL, 
	steps JSONB NOT NULL, 
	generated_by VARCHAR(32) NOT NULL, 
	generated_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_learning_paths PRIMARY KEY (id), 
	CONSTRAINT learning_path_unique UNIQUE (student_id, job_role_id), 
	CONSTRAINT fk_learning_paths_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE, 
	CONSTRAINT fk_learning_paths_job_role_id_job_roles FOREIGN KEY(job_role_id) REFERENCES job_roles (id) ON DELETE CASCADE
);

CREATE INDEX ix_learning_paths_job_role_id ON learning_paths (job_role_id);

CREATE INDEX ix_learning_paths_student_id ON learning_paths (student_id);

CREATE INDEX ix_learning_paths_created_at ON learning_paths (created_at);

CREATE TABLE mentorship_requests (
	id UUID NOT NULL, 
	mentor_id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	topic VARCHAR(200) NOT NULL, 
	message TEXT NOT NULL, 
	goals JSONB NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	preferred_slots JSONB NOT NULL, 
	response_message TEXT NOT NULL, 
	responded_at TIMESTAMP WITH TIME ZONE, 
	match_reason TEXT NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_mentorship_requests PRIMARY KEY (id), 
	CONSTRAINT fk_mentorship_requests_mentor_id_mentors FOREIGN KEY(mentor_id) REFERENCES mentors (id) ON DELETE CASCADE, 
	CONSTRAINT fk_mentorship_requests_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE
);

CREATE INDEX ix_mentorship_requests_mentor_status ON mentorship_requests (mentor_id, status);

CREATE INDEX ix_mentorship_requests_mentor_id ON mentorship_requests (mentor_id);

CREATE INDEX ix_mentorship_requests_created_at ON mentorship_requests (created_at);

CREATE INDEX ix_mentorship_requests_status ON mentorship_requests (status);

CREATE INDEX ix_mentorship_requests_student_id ON mentorship_requests (student_id);

CREATE TABLE conversation_participants (
	id UUID NOT NULL, 
	conversation_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	last_read_at TIMESTAMP WITH TIME ZONE, 
	is_muted BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_conversation_participants PRIMARY KEY (id), 
	CONSTRAINT conversation_participant_unique UNIQUE (conversation_id, user_id), 
	CONSTRAINT fk_conversation_participants_conversation_id_conversations FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE, 
	CONSTRAINT fk_conversation_participants_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_conversation_participants_conversation_id ON conversation_participants (conversation_id);

CREATE INDEX ix_conversation_participants_created_at ON conversation_participants (created_at);

CREATE INDEX ix_conversation_participants_user_id ON conversation_participants (user_id);

CREATE TABLE messages (
	id UUID NOT NULL, 
	conversation_id UUID NOT NULL, 
	sender_id UUID NOT NULL, 
	body TEXT NOT NULL, 
	attachment_document_id UUID, 
	edited_at TIMESTAMP WITH TIME ZONE, 
	is_system BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_messages PRIMARY KEY (id), 
	CONSTRAINT fk_messages_conversation_id_conversations FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE, 
	CONSTRAINT fk_messages_sender_id_users FOREIGN KEY(sender_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT fk_messages_attachment_document_id_documents FOREIGN KEY(attachment_document_id) REFERENCES documents (id) ON DELETE SET NULL
);

CREATE INDEX ix_messages_sender_id ON messages (sender_id);

CREATE INDEX ix_messages_created_at ON messages (created_at);

CREATE INDEX ix_messages_conversation_id ON messages (conversation_id);

CREATE INDEX ix_messages_conversation_created ON messages (conversation_id, created_at);

CREATE TABLE portfolios (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	slug VARCHAR(140) NOT NULL, 
	headline VARCHAR(200) NOT NULL, 
	about TEXT NOT NULL, 
	theme VARCHAR(30) NOT NULL, 
	visibility VARCHAR(24) NOT NULL, 
	sections JSONB NOT NULL, 
	featured_project_ids JSONB NOT NULL, 
	contact_email_visible BOOLEAN NOT NULL, 
	phone_visible BOOLEAN NOT NULL, 
	view_count INTEGER NOT NULL, 
	completion_percentage INTEGER NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_portfolios PRIMARY KEY (id), 
	CONSTRAINT fk_portfolios_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX ix_portfolios_slug ON portfolios (slug);

CREATE INDEX ix_portfolios_created_at ON portfolios (created_at);

CREATE UNIQUE INDEX ix_portfolios_student_id ON portfolios (student_id);

CREATE INDEX ix_portfolios_visibility ON portfolios (visibility);

CREATE TABLE resumes (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	template VARCHAR(30) NOT NULL, 
	content JSONB NOT NULL, 
	target_job_role_id UUID, 
	is_default BOOLEAN NOT NULL, 
	generated_document_id UUID, 
	last_exported_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_resumes PRIMARY KEY (id), 
	CONSTRAINT fk_resumes_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE, 
	CONSTRAINT fk_resumes_target_job_role_id_job_roles FOREIGN KEY(target_job_role_id) REFERENCES job_roles (id) ON DELETE SET NULL, 
	CONSTRAINT fk_resumes_generated_document_id_documents FOREIGN KEY(generated_document_id) REFERENCES documents (id) ON DELETE SET NULL
);

CREATE INDEX ix_resumes_student_id ON resumes (student_id);

CREATE INDEX ix_resumes_created_at ON resumes (created_at);

CREATE TABLE resume_analyses (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	document_id UUID NOT NULL, 
	job_role_id UUID, 
	extracted_skills JSONB NOT NULL, 
	extracted_education JSONB NOT NULL, 
	extracted_experience JSONB NOT NULL, 
	extracted_projects JSONB NOT NULL, 
	extracted_certifications JSONB NOT NULL, 
	matched_skills JSONB NOT NULL, 
	missing_skills JSONB NOT NULL, 
	suggestions JSONB NOT NULL, 
	ats_score INTEGER NOT NULL, 
	analyzed_by VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_resume_analyses PRIMARY KEY (id), 
	CONSTRAINT fk_resume_analyses_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE, 
	CONSTRAINT fk_resume_analyses_document_id_documents FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE, 
	CONSTRAINT fk_resume_analyses_job_role_id_job_roles FOREIGN KEY(job_role_id) REFERENCES job_roles (id) ON DELETE SET NULL
);

CREATE INDEX ix_resume_analyses_created_at ON resume_analyses (created_at);

CREATE INDEX ix_resume_analyses_student_id ON resume_analyses (student_id);

CREATE INDEX ix_resume_analyses_document_id ON resume_analyses (document_id);

CREATE TABLE student_badges (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	badge_id UUID NOT NULL, 
	awarded_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	context JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_student_badges PRIMARY KEY (id), 
	CONSTRAINT student_badge_unique UNIQUE (student_id, badge_id), 
	CONSTRAINT fk_student_badges_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE, 
	CONSTRAINT fk_student_badges_badge_id_badges FOREIGN KEY(badge_id) REFERENCES badges (id) ON DELETE CASCADE
);

CREATE INDEX ix_student_badges_created_at ON student_badges (created_at);

CREATE INDEX ix_student_badges_badge_id ON student_badges (badge_id);

CREATE INDEX ix_student_badges_student_id ON student_badges (student_id);

CREATE TABLE recommendation_feedback (
	id UUID NOT NULL, 
	recommendation_id UUID, 
	user_id UUID NOT NULL, 
	signal VARCHAR(24) NOT NULL, 
	comment VARCHAR(400) NOT NULL, 
	meta JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_recommendation_feedback PRIMARY KEY (id), 
	CONSTRAINT fk_recommendation_feedback_recommendation_id_recommendations FOREIGN KEY(recommendation_id) REFERENCES recommendations (id) ON DELETE SET NULL, 
	CONSTRAINT fk_recommendation_feedback_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_recommendation_feedback_created_at ON recommendation_feedback (created_at);

CREATE INDEX ix_recommendation_feedback_recommendation_id ON recommendation_feedback (recommendation_id);

CREATE INDEX ix_recommendation_feedback_signal ON recommendation_feedback (signal);

CREATE INDEX ix_recommendation_feedback_user_id ON recommendation_feedback (user_id);

CREATE TABLE research_projects (
	id UUID NOT NULL, 
	title VARCHAR(250) NOT NULL, 
	slug VARCHAR(260) NOT NULL, 
	abstract TEXT NOT NULL, 
	project_type VARCHAR(32) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	company_id UUID, 
	institution_id UUID, 
	created_by_id UUID, 
	principal_investigator_id UUID, 
	research_areas JSONB NOT NULL, 
	required_expertise JSONB NOT NULL, 
	deliverables JSONB NOT NULL, 
	funding_amount INTEGER, 
	funding_currency VARCHAR(8) NOT NULL, 
	duration_months INTEGER, 
	starts_on DATE, 
	application_deadline TIMESTAMP WITH TIME ZONE, 
	positions INTEGER NOT NULL, 
	search_text TEXT NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_research_projects PRIMARY KEY (id), 
	CONSTRAINT fk_research_projects_company_id_companies FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE SET NULL, 
	CONSTRAINT fk_research_projects_institution_id_institutions FOREIGN KEY(institution_id) REFERENCES institutions (id) ON DELETE SET NULL, 
	CONSTRAINT fk_research_projects_created_by_id_users FOREIGN KEY(created_by_id) REFERENCES users (id) ON DELETE SET NULL, 
	CONSTRAINT fk_research_projects_principal_investigator_id_academic_1b76 FOREIGN KEY(principal_investigator_id) REFERENCES academician_profiles (id) ON DELETE SET NULL
);

CREATE INDEX ix_research_projects_company_id ON research_projects (company_id);

CREATE INDEX ix_research_projects_principal_investigator_id ON research_projects (principal_investigator_id);

CREATE INDEX ix_research_projects_type_status ON research_projects (project_type, status);

CREATE UNIQUE INDEX ix_research_projects_slug ON research_projects (slug);

CREATE INDEX ix_research_projects_status ON research_projects (status);

CREATE INDEX ix_research_projects_created_at ON research_projects (created_at);

CREATE INDEX ix_research_projects_title ON research_projects (title);

CREATE INDEX ix_research_projects_project_type ON research_projects (project_type);

CREATE INDEX ix_research_projects_institution_id ON research_projects (institution_id);

CREATE INDEX ix_research_projects_deleted_at ON research_projects (deleted_at);

CREATE TABLE skill_gap_items (
	id UUID NOT NULL, 
	analysis_id UUID NOT NULL, 
	skill_id UUID NOT NULL, 
	current_level VARCHAR(16) NOT NULL, 
	required_level VARCHAR(16) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	gap_size INTEGER NOT NULL, 
	priority INTEGER NOT NULL, 
	importance VARCHAR(16) NOT NULL, 
	recommendation TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_skill_gap_items PRIMARY KEY (id), 
	CONSTRAINT skill_gap_item_unique UNIQUE (analysis_id, skill_id), 
	CONSTRAINT fk_skill_gap_items_analysis_id_skill_gap_analyses FOREIGN KEY(analysis_id) REFERENCES skill_gap_analyses (id) ON DELETE CASCADE, 
	CONSTRAINT fk_skill_gap_items_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE CASCADE
);

CREATE INDEX ix_skill_gap_items_analysis_id ON skill_gap_items (analysis_id);

CREATE INDEX ix_skill_gap_items_status ON skill_gap_items (status);

CREATE INDEX ix_skill_gap_items_created_at ON skill_gap_items (created_at);

CREATE TABLE skill_endorsements (
	id UUID NOT NULL, 
	student_skill_id UUID NOT NULL, 
	endorsed_by_user_id UUID NOT NULL, 
	note VARCHAR(400) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_skill_endorsements PRIMARY KEY (id), 
	CONSTRAINT endorsement_unique UNIQUE (student_skill_id, endorsed_by_user_id), 
	CONSTRAINT fk_skill_endorsements_student_skill_id_student_skills FOREIGN KEY(student_skill_id) REFERENCES student_skills (id) ON DELETE CASCADE, 
	CONSTRAINT fk_skill_endorsements_endorsed_by_user_id_users FOREIGN KEY(endorsed_by_user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_skill_endorsements_created_at ON skill_endorsements (created_at);

CREATE INDEX ix_skill_endorsements_student_skill_id ON skill_endorsements (student_skill_id);

CREATE TABLE application_status_history (
	id UUID NOT NULL, 
	application_id UUID NOT NULL, 
	from_status VARCHAR(20), 
	to_status VARCHAR(20) NOT NULL, 
	changed_by_id UUID, 
	note TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_application_status_history PRIMARY KEY (id), 
	CONSTRAINT fk_application_status_history_application_id_applications FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE, 
	CONSTRAINT fk_application_status_history_changed_by_id_users FOREIGN KEY(changed_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_application_status_history_created_at ON application_status_history (created_at);

CREATE INDEX ix_application_status_history_application_id ON application_status_history (application_id);

CREATE TABLE interviews (
	id UUID NOT NULL, 
	application_id UUID NOT NULL, 
	round_number INTEGER NOT NULL, 
	round_name VARCHAR(120) NOT NULL, 
	mode VARCHAR(20) NOT NULL, 
	scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	duration_minutes INTEGER NOT NULL, 
	location_or_link VARCHAR(400), 
	interviewer_user_id UUID, 
	interviewer_name VARCHAR(160), 
	status VARCHAR(20) NOT NULL, 
	feedback TEXT NOT NULL, 
	rating INTEGER, 
	instructions TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_interviews PRIMARY KEY (id), 
	CONSTRAINT fk_interviews_application_id_applications FOREIGN KEY(application_id) REFERENCES applications (id) ON DELETE CASCADE, 
	CONSTRAINT fk_interviews_interviewer_user_id_users FOREIGN KEY(interviewer_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_interviews_application_id ON interviews (application_id);

CREATE INDEX ix_interviews_scheduled ON interviews (scheduled_at, status);

CREATE INDEX ix_interviews_created_at ON interviews (created_at);

CREATE TABLE assessment_options (
	id UUID NOT NULL, 
	question_id UUID NOT NULL, 
	label TEXT NOT NULL, 
	is_correct BOOLEAN NOT NULL, 
	proficiency_value INTEGER, 
	display_order INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_assessment_options PRIMARY KEY (id), 
	CONSTRAINT fk_assessment_options_question_id_assessment_questions FOREIGN KEY(question_id) REFERENCES assessment_questions (id) ON DELETE CASCADE
);

CREATE INDEX ix_assessment_options_question_id ON assessment_options (question_id);

CREATE INDEX ix_assessment_options_created_at ON assessment_options (created_at);

CREATE TABLE assessment_answers (
	id UUID NOT NULL, 
	attempt_id UUID NOT NULL, 
	question_id UUID NOT NULL, 
	selected_option_ids JSONB NOT NULL, 
	free_text TEXT, 
	is_correct BOOLEAN NOT NULL, 
	awarded_score FLOAT NOT NULL, 
	max_score FLOAT NOT NULL, 
	time_spent_seconds INTEGER, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_assessment_answers PRIMARY KEY (id), 
	CONSTRAINT attempt_question_unique UNIQUE (attempt_id, question_id), 
	CONSTRAINT fk_assessment_answers_attempt_id_assessment_attempts FOREIGN KEY(attempt_id) REFERENCES assessment_attempts (id) ON DELETE CASCADE, 
	CONSTRAINT fk_assessment_answers_question_id_assessment_questions FOREIGN KEY(question_id) REFERENCES assessment_questions (id) ON DELETE CASCADE
);

CREATE INDEX ix_assessment_answers_created_at ON assessment_answers (created_at);

CREATE INDEX ix_assessment_answers_attempt_id ON assessment_answers (attempt_id);

CREATE TABLE attempt_skill_scores (
	id UUID NOT NULL, 
	attempt_id UUID NOT NULL, 
	skill_id UUID NOT NULL, 
	score FLOAT NOT NULL, 
	max_score FLOAT NOT NULL, 
	percentage FLOAT NOT NULL, 
	questions_count INTEGER NOT NULL, 
	correct_count INTEGER NOT NULL, 
	confidence FLOAT NOT NULL, 
	level VARCHAR(16) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_attempt_skill_scores PRIMARY KEY (id), 
	CONSTRAINT attempt_skill_unique UNIQUE (attempt_id, skill_id), 
	CONSTRAINT fk_attempt_skill_scores_attempt_id_assessment_attempts FOREIGN KEY(attempt_id) REFERENCES assessment_attempts (id) ON DELETE CASCADE, 
	CONSTRAINT fk_attempt_skill_scores_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE CASCADE
);

CREATE INDEX ix_attempt_skill_scores_skill_id ON attempt_skill_scores (skill_id);

CREATE INDEX ix_attempt_skill_scores_created_at ON attempt_skill_scores (created_at);

CREATE INDEX ix_attempt_skill_scores_attempt_id ON attempt_skill_scores (attempt_id);

CREATE TABLE module_progress (
	id UUID NOT NULL, 
	enrollment_id UUID NOT NULL, 
	module_id UUID NOT NULL, 
	is_completed BOOLEAN NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	time_spent_minutes INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_module_progress PRIMARY KEY (id), 
	CONSTRAINT module_progress_unique UNIQUE (enrollment_id, module_id), 
	CONSTRAINT fk_module_progress_enrollment_id_enrollments FOREIGN KEY(enrollment_id) REFERENCES enrollments (id) ON DELETE CASCADE, 
	CONSTRAINT fk_module_progress_module_id_course_modules FOREIGN KEY(module_id) REFERENCES course_modules (id) ON DELETE CASCADE
);

CREATE INDEX ix_module_progress_created_at ON module_progress (created_at);

CREATE INDEX ix_module_progress_enrollment_id ON module_progress (enrollment_id);

CREATE TABLE student_certifications (
	id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	certification_id UUID, 
	enrollment_id UUID, 
	name VARCHAR(200) NOT NULL, 
	issuer VARCHAR(180) NOT NULL, 
	credential_id VARCHAR(160), 
	credential_url VARCHAR(500), 
	issued_on DATE, 
	expires_on DATE, 
	document_id UUID, 
	skill_ids JSONB NOT NULL, 
	verification_status VARCHAR(20) NOT NULL, 
	verified_by_id UUID, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_student_certifications PRIMARY KEY (id), 
	CONSTRAINT fk_student_certifications_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE, 
	CONSTRAINT fk_student_certifications_certification_id_certifications FOREIGN KEY(certification_id) REFERENCES certifications (id) ON DELETE SET NULL, 
	CONSTRAINT fk_student_certifications_enrollment_id_enrollments FOREIGN KEY(enrollment_id) REFERENCES enrollments (id) ON DELETE SET NULL, 
	CONSTRAINT fk_student_certifications_document_id_documents FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE SET NULL, 
	CONSTRAINT fk_student_certifications_verified_by_id_users FOREIGN KEY(verified_by_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_student_certifications_student ON student_certifications (student_id, verification_status);

CREATE INDEX ix_student_certifications_student_id ON student_certifications (student_id);

CREATE INDEX ix_student_certifications_certification_id ON student_certifications (certification_id);

CREATE INDEX ix_student_certifications_created_at ON student_certifications (created_at);

CREATE TABLE mentorship_sessions (
	id UUID NOT NULL, 
	request_id UUID NOT NULL, 
	scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	duration_minutes INTEGER NOT NULL, 
	meeting_link VARCHAR(400), 
	agenda TEXT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	mentor_notes TEXT NOT NULL, 
	student_notes TEXT NOT NULL, 
	action_items JSONB NOT NULL, 
	student_rating INTEGER, 
	student_feedback TEXT NOT NULL, 
	mentor_rating INTEGER, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_mentorship_sessions PRIMARY KEY (id), 
	CONSTRAINT fk_mentorship_sessions_request_id_mentorship_requests FOREIGN KEY(request_id) REFERENCES mentorship_requests (id) ON DELETE CASCADE
);

CREATE INDEX ix_mentorship_sessions_scheduled_at ON mentorship_sessions (scheduled_at);

CREATE INDEX ix_mentorship_sessions_created_at ON mentorship_sessions (created_at);

CREATE INDEX ix_mentorship_sessions_request_id ON mentorship_sessions (request_id);

CREATE INDEX ix_mentorship_sessions_status ON mentorship_sessions (status);

CREATE TABLE project_teams (
	id UUID NOT NULL, 
	project_id UUID NOT NULL, 
	name VARCHAR(140) NOT NULL, 
	lead_student_id UUID, 
	status VARCHAR(20) NOT NULL, 
	pitch TEXT NOT NULL, 
	score FLOAT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_project_teams PRIMARY KEY (id), 
	CONSTRAINT project_team_name_unique UNIQUE (project_id, name), 
	CONSTRAINT fk_project_teams_project_id_live_projects FOREIGN KEY(project_id) REFERENCES live_projects (id) ON DELETE CASCADE, 
	CONSTRAINT fk_project_teams_lead_student_id_student_profiles FOREIGN KEY(lead_student_id) REFERENCES student_profiles (id) ON DELETE SET NULL
);

CREATE INDEX ix_project_teams_created_at ON project_teams (created_at);

CREATE INDEX ix_project_teams_status ON project_teams (status);

CREATE INDEX ix_project_teams_project_id ON project_teams (project_id);

CREATE TABLE research_applications (
	id UUID NOT NULL, 
	project_id UUID NOT NULL, 
	academician_id UUID NOT NULL, 
	proposal TEXT NOT NULL, 
	relevant_publications JSONB NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	reviewer_notes TEXT NOT NULL, 
	decided_at TIMESTAMP WITH TIME ZONE, 
	is_demo BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_research_applications PRIMARY KEY (id), 
	CONSTRAINT research_application_unique UNIQUE (project_id, academician_id), 
	CONSTRAINT fk_research_applications_project_id_research_projects FOREIGN KEY(project_id) REFERENCES research_projects (id) ON DELETE CASCADE, 
	CONSTRAINT fk_research_applications_academician_id_academician_profiles FOREIGN KEY(academician_id) REFERENCES academician_profiles (id) ON DELETE CASCADE
);

CREATE INDEX ix_research_applications_status ON research_applications (status);

CREATE INDEX ix_research_applications_created_at ON research_applications (created_at);

CREATE INDEX ix_research_applications_academician_id ON research_applications (academician_id);

CREATE INDEX ix_research_applications_project_id ON research_applications (project_id);

CREATE TABLE project_team_members (
	id UUID NOT NULL, 
	team_id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	role_in_team VARCHAR(80) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_project_team_members PRIMARY KEY (id), 
	CONSTRAINT project_member_unique UNIQUE (team_id, student_id), 
	CONSTRAINT fk_project_team_members_team_id_project_teams FOREIGN KEY(team_id) REFERENCES project_teams (id) ON DELETE CASCADE, 
	CONSTRAINT fk_project_team_members_student_id_student_profiles FOREIGN KEY(student_id) REFERENCES student_profiles (id) ON DELETE CASCADE
);

CREATE INDEX ix_project_team_members_student_id ON project_team_members (student_id);

CREATE INDEX ix_project_team_members_team_id ON project_team_members (team_id);

CREATE INDEX ix_project_team_members_created_at ON project_team_members (created_at);

CREATE TABLE project_milestones (
	id UUID NOT NULL, 
	project_id UUID NOT NULL, 
	team_id UUID, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	due_on DATE, 
	display_order INTEGER NOT NULL, 
	weight FLOAT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_project_milestones PRIMARY KEY (id), 
	CONSTRAINT fk_project_milestones_project_id_live_projects FOREIGN KEY(project_id) REFERENCES live_projects (id) ON DELETE CASCADE, 
	CONSTRAINT fk_project_milestones_team_id_project_teams FOREIGN KEY(team_id) REFERENCES project_teams (id) ON DELETE CASCADE
);

CREATE INDEX ix_project_milestones_created_at ON project_milestones (created_at);

CREATE INDEX ix_project_milestones_project_id ON project_milestones (project_id);

CREATE INDEX ix_project_milestones_status ON project_milestones (status);

CREATE INDEX ix_project_milestones_project_order ON project_milestones (project_id, display_order);

CREATE INDEX ix_project_milestones_team_id ON project_milestones (team_id);

CREATE TABLE project_tasks (
	id UUID NOT NULL, 
	milestone_id UUID NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	assignee_student_id UUID, 
	status VARCHAR(20) NOT NULL, 
	due_on DATE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_project_tasks PRIMARY KEY (id), 
	CONSTRAINT fk_project_tasks_milestone_id_project_milestones FOREIGN KEY(milestone_id) REFERENCES project_milestones (id) ON DELETE CASCADE, 
	CONSTRAINT fk_project_tasks_assignee_student_id_student_profiles FOREIGN KEY(assignee_student_id) REFERENCES student_profiles (id) ON DELETE SET NULL
);

CREATE INDEX ix_project_tasks_assignee_student_id ON project_tasks (assignee_student_id);

CREATE INDEX ix_project_tasks_created_at ON project_tasks (created_at);

CREATE INDEX ix_project_tasks_milestone_id ON project_tasks (milestone_id);

CREATE INDEX ix_project_tasks_status ON project_tasks (status);

CREATE TABLE project_submissions (
	id UUID NOT NULL, 
	milestone_id UUID NOT NULL, 
	team_id UUID, 
	submitted_by_student_id UUID, 
	summary TEXT NOT NULL, 
	repository_url VARCHAR(400), 
	document_id UUID, 
	submitted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	score FLOAT, 
	evaluator_user_id UUID, 
	feedback TEXT NOT NULL, 
	evaluated_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_project_submissions PRIMARY KEY (id), 
	CONSTRAINT fk_project_submissions_milestone_id_project_milestones FOREIGN KEY(milestone_id) REFERENCES project_milestones (id) ON DELETE CASCADE, 
	CONSTRAINT fk_project_submissions_team_id_project_teams FOREIGN KEY(team_id) REFERENCES project_teams (id) ON DELETE SET NULL, 
	CONSTRAINT fk_project_submissions_submitted_by_student_id_student_profiles FOREIGN KEY(submitted_by_student_id) REFERENCES student_profiles (id) ON DELETE SET NULL, 
	CONSTRAINT fk_project_submissions_document_id_documents FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE SET NULL, 
	CONSTRAINT fk_project_submissions_evaluator_user_id_users FOREIGN KEY(evaluator_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_project_submissions_team_id ON project_submissions (team_id);

CREATE INDEX ix_project_submissions_created_at ON project_submissions (created_at);

CREATE INDEX ix_project_submissions_milestone_id ON project_submissions (milestone_id);
