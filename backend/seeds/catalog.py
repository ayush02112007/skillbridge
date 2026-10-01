"""Canonical reference data: skill taxonomy and job-role requirements.

This is *catalogue* data, not demo data - it is what makes the platform useful
on day one, and the admin panel extends it at runtime. Demo users, companies and
postings live in ``seeds/seed.py`` and are flagged ``is_demo=True``.
"""
from __future__ import annotations

# (category slug, display name, icon, colour, is_soft_skill)
CATEGORIES: list[tuple[str, str, str, str, bool]] = [
    ("programming", "Programming Languages", "code", "#1c5d99", False),
    ("backend", "Backend Development", "server", "#2a7f62", False),
    ("frontend", "Frontend Development", "layout", "#7c5cbf", False),
    ("database", "Databases", "database", "#b45309", False),
    ("cloud", "Cloud Platforms", "cloud", "#0e7490", False),
    ("devops", "DevOps & Infrastructure", "settings", "#475569", False),
    ("ai", "Artificial Intelligence", "brain", "#be123c", False),
    ("data-science", "Data Science & Analytics", "bar-chart-3", "#0f766e", False),
    ("cybersecurity", "Cybersecurity", "shield", "#9333ea", False),
    ("mobile", "Mobile Development", "smartphone", "#c2410c", False),
    ("testing", "Testing & Quality", "check-circle", "#0369a1", False),
    ("design", "Design & User Experience", "palette", "#db2777", False),
    ("product", "Product & Business", "briefcase", "#4d7c0f", False),
    ("soft-skills", "Professional Skills", "users", "#64748b", True),
]

# (skill slug, name, category slug, aliases, demand_score 0-100, trending)
SKILLS: list[tuple[str, str, str, list[str], int, bool]] = [
    # -- programming
    ("python", "Python", "programming", ["py", "python3"], 95, True),
    ("java", "Java", "programming", ["core java", "java se"], 88, False),
    ("javascript", "JavaScript", "programming", ["js", "ecmascript", "es6"], 92, False),
    ("typescript", "TypeScript", "programming", ["ts"], 86, True),
    ("c-plus-plus", "C++", "programming", ["cpp", "c ++"], 72, False),
    ("c-language", "C", "programming", ["c programming"], 65, False),
    ("csharp", "C#", "programming", ["c sharp", "dotnet language"], 64, False),
    ("go", "Go", "programming", ["golang"], 70, True),
    ("rust", "Rust", "programming", [], 55, True),
    ("kotlin", "Kotlin", "programming", [], 58, False),
    ("swift", "Swift", "programming", [], 52, False),
    ("php", "PHP", "programming", [], 48, False),
    ("ruby", "Ruby", "programming", [], 40, False),
    ("r-language", "R", "programming", ["r programming"], 45, False),
    ("sql", "SQL", "programming", ["structured query language", "ansi sql"], 94, False),
    ("shell-scripting", "Shell Scripting", "programming", ["bash", "zsh", "shell"], 66, False),
    # -- backend
    ("fastapi", "FastAPI", "backend", ["fast api"], 78, True),
    ("django", "Django", "backend", ["django rest framework", "drf"], 74, False),
    ("flask", "Flask", "backend", [], 62, False),
    ("spring-boot", "Spring Boot", "backend", ["spring", "springboot"], 82, False),
    ("nodejs", "Node.js", "backend", ["node", "nodejs"], 87, False),
    ("express", "Express.js", "backend", ["expressjs"], 72, False),
    ("nestjs", "NestJS", "backend", ["nest js"], 50, True),
    ("dotnet-core", ".NET Core", "backend", ["asp.net core", "dotnet"], 60, False),
    ("rest-api", "REST API Design", "backend", ["rest", "restful api", "api design"], 93, False),
    ("graphql", "GraphQL", "backend", [], 58, False),
    ("grpc", "gRPC", "backend", [], 42, False),
    ("microservices", "Microservices Architecture", "backend", ["micro services"], 76, False),
    ("message-queues", "Message Queues", "backend", ["kafka", "rabbitmq", "celery"], 64, False),
    ("system-design", "System Design", "backend", ["hld", "lld", "architecture design"], 84, True),
    # -- frontend
    ("react", "React", "frontend", ["reactjs", "react.js"], 93, False),
    ("nextjs", "Next.js", "frontend", ["next js", "nextjs"], 80, True),
    ("vue", "Vue.js", "frontend", ["vuejs"], 58, False),
    ("angular", "Angular", "frontend", ["angularjs"], 62, False),
    ("html", "HTML5", "frontend", ["html"], 85, False),
    ("css", "CSS3", "frontend", ["css", "scss", "sass"], 84, False),
    ("tailwind", "Tailwind CSS", "frontend", ["tailwindcss"], 70, True),
    ("redux", "State Management", "frontend", ["redux", "zustand", "context api"], 64, False),
    ("web-accessibility", "Web Accessibility", "frontend", ["a11y", "wcag"], 48, True),
    ("responsive-design", "Responsive Design", "frontend", ["mobile first design"], 72, False),
    # -- database
    ("postgresql", "PostgreSQL", "database", ["postgres", "psql"], 89, False),
    ("mysql", "MySQL", "database", ["mariadb"], 76, False),
    ("mongodb", "MongoDB", "database", ["mongo"], 71, False),
    ("redis", "Redis", "database", [], 68, False),
    ("elasticsearch", "Elasticsearch", "database", ["opensearch", "elastic"], 52, False),
    ("database-design", "Database Design", "database", ["schema design", "normalization", "er modelling"], 80, False),
    ("query-optimization", "Query Optimisation", "database", ["indexing", "explain plan"], 66, False),
    # -- cloud
    ("aws", "AWS", "cloud", ["amazon web services", "ec2", "s3"], 91, False),
    ("azure", "Microsoft Azure", "cloud", ["azure"], 78, False),
    ("gcp", "Google Cloud", "cloud", ["google cloud platform", "gcp"], 66, False),
    ("serverless", "Serverless", "cloud", ["lambda", "cloud functions"], 58, True),
    ("cloud-architecture", "Cloud Architecture", "cloud", ["well architected"], 70, False),
    # -- devops
    ("docker", "Docker", "devops", ["containers", "containerisation"], 88, False),
    ("kubernetes", "Kubernetes", "devops", ["k8s", "eks", "aks"], 77, True),
    ("ci-cd", "CI/CD", "devops", ["continuous integration", "continuous delivery"], 85, False),
    ("github-actions", "GitHub Actions", "devops", ["gh actions"], 64, False),
    ("jenkins", "Jenkins", "devops", [], 55, False),
    ("terraform", "Terraform", "devops", ["infrastructure as code", "iac"], 68, True),
    ("ansible", "Ansible", "devops", ["configuration management"], 46, False),
    ("linux", "Linux", "devops", ["unix", "ubuntu"], 82, False),
    ("nginx", "Nginx", "devops", ["reverse proxy"], 58, False),
    ("observability", "Monitoring & Observability", "devops", ["prometheus", "grafana", "logging"], 66, True),
    ("git", "Git", "devops", ["version control", "github", "gitlab"], 95, False),
    # -- ai
    ("machine-learning", "Machine Learning", "ai", ["ml", "supervised learning"], 90, True),
    ("deep-learning", "Deep Learning", "ai", ["neural networks", "dl"], 80, True),
    ("nlp", "Natural Language Processing", "ai", ["nlp", "text mining"], 78, True),
    ("computer-vision", "Computer Vision", "ai", ["cv", "image processing", "opencv"], 68, False),
    ("mlops", "MLOps", "ai", ["ml ops", "model deployment"], 66, True),
    ("llm-engineering", "LLM Engineering", "ai", ["large language models", "rag", "prompt engineering"], 82, True),
    ("reinforcement-learning", "Reinforcement Learning", "ai", ["rl"], 42, False),
    ("responsible-ai", "Responsible AI", "ai", ["ai ethics", "model fairness"], 50, True),
    # -- data science
    ("pandas", "Pandas", "data-science", ["dataframes"], 86, False),
    ("numpy", "NumPy", "data-science", [], 80, False),
    ("scikit-learn", "scikit-learn", "data-science", ["sklearn"], 79, False),
    ("tensorflow", "TensorFlow", "data-science", ["keras"], 68, False),
    ("pytorch", "PyTorch", "data-science", ["torch"], 74, True),
    ("data-visualization", "Data Visualisation", "data-science", ["matplotlib", "seaborn", "charts"], 76, False),
    ("statistics", "Statistics", "data-science", ["probability", "hypothesis testing"], 78, False),
    ("feature-engineering", "Feature Engineering", "data-science", [], 66, False),
    ("spark", "Apache Spark", "data-science", ["pyspark", "big data"], 60, False),
    ("etl", "ETL & Data Pipelines", "data-science", ["airflow", "data pipeline", "dbt"], 72, False),
    ("power-bi", "Power BI", "data-science", ["powerbi"], 64, False),
    ("tableau", "Tableau", "data-science", [], 58, False),
    ("excel", "Advanced Excel", "data-science", ["spreadsheets", "pivot tables"], 70, False),
    # -- cybersecurity
    ("network-security", "Network Security", "cybersecurity", ["firewall", "vpn"], 72, False),
    ("application-security", "Application Security", "cybersecurity", ["appsec", "secure coding"], 74, True),
    ("penetration-testing", "Penetration Testing", "cybersecurity", ["pentesting", "ethical hacking"], 68, False),
    ("cryptography", "Cryptography", "cybersecurity", ["encryption", "pki"], 58, False),
    ("siem", "SIEM & Threat Detection", "cybersecurity", ["splunk", "threat hunting"], 60, False),
    ("incident-response", "Incident Response", "cybersecurity", ["soc", "forensics"], 62, False),
    ("owasp", "OWASP Top 10", "cybersecurity", ["owasp"], 70, False),
    ("iam", "Identity & Access Management", "cybersecurity", ["iam", "sso", "oauth"], 66, False),
    # -- mobile
    ("android", "Android Development", "mobile", ["android sdk", "jetpack compose"], 70, False),
    ("ios", "iOS Development", "mobile", ["swiftui", "xcode"], 58, False),
    ("react-native", "React Native", "mobile", ["rn"], 64, False),
    ("flutter", "Flutter", "mobile", ["dart"], 66, True),
    # -- testing
    ("unit-testing", "Unit Testing", "testing", ["tdd"], 80, False),
    ("pytest", "Pytest", "testing", [], 62, False),
    ("jest", "Jest", "testing", ["vitest"], 58, False),
    ("selenium", "Selenium", "testing", [], 54, False),
    ("playwright", "Playwright", "testing", ["cypress", "e2e testing"], 60, True),
    ("test-automation", "Test Automation", "testing", ["automation testing"], 72, False),
    ("manual-testing", "Manual & Exploratory Testing", "testing", ["qa testing"], 55, False),
    # -- design
    ("ui-design", "UI Design", "design", ["visual design", "interface design"], 70, False),
    ("ux-research", "UX Research", "design", ["user research", "usability testing"], 66, False),
    ("figma", "Figma", "design", ["sketch", "adobe xd"], 74, False),
    ("wireframing", "Wireframing & Prototyping", "design", ["prototyping", "mockups"], 68, False),
    ("design-systems", "Design Systems", "design", ["component library"], 58, True),
    ("interaction-design", "Interaction Design", "design", ["motion design", "microinteractions"], 52, False),
    # -- product & business
    ("product-management", "Product Management", "product", ["product owner"], 76, False),
    ("agile", "Agile & Scrum", "product", ["scrum", "kanban", "sprint planning"], 82, False),
    ("roadmapping", "Roadmapping & Prioritisation", "product", ["rice", "moscow"], 62, False),
    ("business-analysis", "Business Analysis", "product", ["ba"], 70, False),
    ("requirements-gathering", "Requirements Gathering", "product", ["brd", "user stories"], 72, False),
    ("stakeholder-management", "Stakeholder Management", "product", [], 68, False),
    ("market-research", "Market Research", "product", ["competitive analysis"], 56, False),
    ("jira", "JIRA & Project Tracking", "product", ["jira", "confluence", "asana"], 66, False),
    ("product-analytics", "Product Analytics", "product", ["mixpanel", "amplitude", "ga4"], 60, True),
    # -- soft skills
    ("communication", "Communication", "soft-skills", ["verbal communication", "written communication"], 96, False),
    ("leadership", "Leadership", "soft-skills", ["people management"], 82, False),
    ("teamwork", "Teamwork & Collaboration", "soft-skills", ["collaboration"], 94, False),
    ("problem-solving", "Problem Solving", "soft-skills", ["analytical thinking"], 95, False),
    ("critical-thinking", "Critical Thinking", "soft-skills", [], 84, False),
    ("time-management", "Time Management", "soft-skills", ["prioritisation"], 80, False),
    ("adaptability", "Adaptability", "soft-skills", ["learning agility"], 78, False),
    ("presentation", "Presentation Skills", "soft-skills", ["public speaking"], 74, False),
    ("ownership", "Ownership & Accountability", "soft-skills", ["initiative"], 80, False),
    ("customer-focus", "Customer Focus", "soft-skills", ["empathy", "user empathy"], 70, False),
]

# Proficiency shorthand: keeps the role table below readable at a glance.
# (`I` on its own is easily misread as a pipe or a 1, hence the longer names.)
BEG, INT, ADV, EXP = "BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"
REQ, PREF = "REQUIRED", "PREFERRED"

# role slug -> (title, family, seniority, salary_min, salary_max, demand,
#               description, [(skill slug, level, importance, weight)])
JOB_ROLES: dict[str, dict] = {
    "backend-developer": {
        "title": "Backend Developer", "family": "Engineering", "seniority": "ENTRY",
        "salary": (600000, 1400000), "demand": 92,
        "description": "Designs and builds server-side services, APIs and data models "
                       "that power products at scale.",
        "responsibilities": [
            "Design and implement REST APIs and background services",
            "Model relational data and write efficient queries",
            "Write automated tests and participate in code review",
            "Deploy and monitor services in a containerised environment",
        ],
        "skills": [
            ("python", ADV, REQ, 1.4), ("rest-api", ADV, REQ, 1.4),
            ("postgresql", ADV, REQ, 1.3), ("sql", ADV, REQ, 1.2),
            ("git", INT, REQ, 1.0), ("docker", INT, REQ, 1.1),
            ("fastapi", INT, REQ, 1.2), ("system-design", INT, REQ, 1.1),
            ("unit-testing", INT, REQ, 1.0), ("linux", INT, PREF, 0.8),
            ("aws", INT, PREF, 0.9), ("redis", BEG, PREF, 0.7),
            ("message-queues", BEG, PREF, 0.7), ("microservices", BEG, PREF, 0.8),
            ("problem-solving", ADV, REQ, 1.0), ("communication", INT, REQ, 0.8),
        ],
    },
    "frontend-developer": {
        "title": "Frontend Developer", "family": "Engineering", "seniority": "ENTRY",
        "salary": (550000, 1300000), "demand": 88,
        "description": "Builds accessible, responsive user interfaces and connects them "
                       "to backend services.",
        "responsibilities": [
            "Translate designs into responsive, accessible components",
            "Manage client state and integrate REST/GraphQL APIs",
            "Optimise bundle size, rendering and Core Web Vitals",
            "Write component and end-to-end tests",
        ],
        "skills": [
            ("javascript", ADV, REQ, 1.4), ("react", ADV, REQ, 1.4),
            ("html", ADV, REQ, 1.1), ("css", ADV, REQ, 1.1),
            ("typescript", INT, REQ, 1.2), ("responsive-design", INT, REQ, 1.0),
            ("git", INT, REQ, 1.0), ("rest-api", INT, REQ, 1.0),
            ("redux", INT, REQ, 0.9), ("nextjs", INT, PREF, 0.9),
            ("tailwind", INT, PREF, 0.8), ("web-accessibility", BEG, PREF, 0.8),
            ("jest", BEG, PREF, 0.7), ("figma", BEG, PREF, 0.6),
            ("problem-solving", INT, REQ, 0.9), ("teamwork", INT, REQ, 0.8),
        ],
    },
    "full-stack-developer": {
        "title": "Full Stack Developer", "family": "Engineering", "seniority": "ENTRY",
        "salary": (650000, 1600000), "demand": 90,
        "description": "Owns features end to end, from database schema through API to "
                       "user interface.",
        "responsibilities": [
            "Ship features across database, API and UI layers",
            "Own deployment and observability for the features you build",
            "Collaborate with design and product on scope and trade-offs",
        ],
        "skills": [
            ("javascript", ADV, REQ, 1.3), ("react", ADV, REQ, 1.3),
            ("nodejs", INT, REQ, 1.1), ("python", INT, REQ, 1.1),
            ("rest-api", ADV, REQ, 1.2), ("postgresql", INT, REQ, 1.2),
            ("sql", INT, REQ, 1.1), ("git", INT, REQ, 1.0),
            ("docker", INT, REQ, 1.0), ("typescript", INT, PREF, 0.9),
            ("nextjs", INT, PREF, 0.9), ("aws", BEG, PREF, 0.8),
            ("system-design", INT, PREF, 0.9), ("unit-testing", INT, PREF, 0.8),
            ("problem-solving", ADV, REQ, 1.0), ("ownership", INT, REQ, 0.8),
        ],
    },
    "python-developer": {
        "title": "Python Developer", "family": "Engineering", "seniority": "ENTRY",
        "salary": (550000, 1300000), "demand": 86,
        "description": "Builds applications, automation and data tooling in Python.",
        "responsibilities": [
            "Write clean, tested Python for services and automation",
            "Integrate third-party APIs and internal services",
            "Profile and optimise slow code paths",
        ],
        "skills": [
            ("python", EXP, REQ, 1.5), ("sql", INT, REQ, 1.1),
            ("git", INT, REQ, 1.0), ("rest-api", INT, REQ, 1.1),
            ("unit-testing", INT, REQ, 1.0), ("pytest", INT, REQ, 0.9),
            ("django", INT, PREF, 0.9), ("fastapi", INT, PREF, 0.9),
            ("pandas", BEG, PREF, 0.7), ("docker", BEG, PREF, 0.8),
            ("linux", INT, PREF, 0.7), ("problem-solving", ADV, REQ, 1.0),
            ("communication", INT, REQ, 0.7),
        ],
    },
    "java-developer": {
        "title": "Java Developer", "family": "Engineering", "seniority": "ENTRY",
        "salary": (600000, 1400000), "demand": 84,
        "description": "Builds enterprise-grade backend services on the JVM.",
        "responsibilities": [
            "Develop Spring Boot microservices",
            "Write JUnit tests and maintain build pipelines",
            "Tune JVM and database performance",
        ],
        "skills": [
            ("java", EXP, REQ, 1.5), ("spring-boot", ADV, REQ, 1.3),
            ("sql", ADV, REQ, 1.2), ("rest-api", ADV, REQ, 1.2),
            ("git", INT, REQ, 1.0), ("mysql", INT, REQ, 1.0),
            ("unit-testing", INT, REQ, 1.0), ("microservices", INT, PREF, 0.9),
            ("docker", INT, PREF, 0.8), ("kubernetes", BEG, PREF, 0.7),
            ("system-design", INT, PREF, 0.9), ("problem-solving", ADV, REQ, 1.0),
        ],
    },
    "data-scientist": {
        "title": "Data Scientist", "family": "Data & AI", "seniority": "ENTRY",
        "salary": (800000, 2000000), "demand": 89,
        "description": "Turns data into decisions using statistics, modelling and "
                       "clear communication.",
        "responsibilities": [
            "Frame business questions as measurable problems",
            "Build, validate and interpret statistical and ML models",
            "Communicate findings to non-technical stakeholders",
        ],
        "skills": [
            ("python", ADV, REQ, 1.4), ("statistics", ADV, REQ, 1.4),
            ("machine-learning", ADV, REQ, 1.4), ("pandas", ADV, REQ, 1.2),
            ("numpy", INT, REQ, 1.0), ("scikit-learn", ADV, REQ, 1.2),
            ("sql", ADV, REQ, 1.2), ("data-visualization", INT, REQ, 1.0),
            ("feature-engineering", INT, REQ, 1.0), ("deep-learning", BEG, PREF, 0.8),
            ("spark", BEG, PREF, 0.6), ("communication", ADV, REQ, 1.1),
            ("critical-thinking", ADV, REQ, 1.0), ("responsible-ai", BEG, PREF, 0.7),
        ],
    },
    "ml-engineer": {
        "title": "Machine Learning Engineer", "family": "Data & AI", "seniority": "ENTRY",
        "salary": (900000, 2200000), "demand": 91,
        "description": "Takes models from notebook to production and keeps them healthy.",
        "responsibilities": [
            "Productionise models as reliable, monitored services",
            "Build reproducible training and evaluation pipelines",
            "Own model performance, drift and rollback",
        ],
        "skills": [
            ("python", ADV, REQ, 1.4), ("machine-learning", ADV, REQ, 1.4),
            ("pytorch", INT, REQ, 1.1), ("scikit-learn", ADV, REQ, 1.1),
            ("mlops", INT, REQ, 1.2), ("docker", INT, REQ, 1.1),
            ("sql", INT, REQ, 1.0), ("rest-api", INT, REQ, 1.0),
            ("aws", INT, PREF, 0.9), ("kubernetes", BEG, PREF, 0.8),
            ("deep-learning", INT, REQ, 1.1), ("etl", INT, PREF, 0.8),
            ("problem-solving", ADV, REQ, 1.0),
        ],
    },
    "ai-engineer": {
        "title": "AI Engineer", "family": "Data & AI", "seniority": "ENTRY",
        "salary": (1000000, 2400000), "demand": 93,
        "description": "Builds products on top of foundation models: retrieval, "
                       "orchestration, evaluation and safety.",
        "responsibilities": [
            "Design retrieval-augmented and agentic application flows",
            "Build evaluation harnesses for model quality and safety",
            "Integrate model APIs behind resilient service boundaries",
        ],
        "skills": [
            ("python", ADV, REQ, 1.4), ("llm-engineering", ADV, REQ, 1.5),
            ("nlp", INT, REQ, 1.2), ("rest-api", INT, REQ, 1.0),
            ("machine-learning", INT, REQ, 1.1), ("docker", INT, REQ, 0.9),
            ("responsible-ai", INT, REQ, 1.0), ("system-design", INT, PREF, 0.9),
            ("deep-learning", INT, PREF, 0.9), ("aws", BEG, PREF, 0.7),
            ("critical-thinking", ADV, REQ, 1.0),
        ],
    },
    "data-analyst": {
        "title": "Data Analyst", "family": "Data & AI", "seniority": "ENTRY",
        "salary": (450000, 1000000), "demand": 82,
        "description": "Answers business questions with data and makes the answer obvious.",
        "responsibilities": [
            "Build dashboards and recurring reports",
            "Run ad-hoc analyses for business teams",
            "Define and maintain metric definitions",
        ],
        "skills": [
            ("sql", ADV, REQ, 1.5), ("excel", ADV, REQ, 1.1),
            ("data-visualization", ADV, REQ, 1.2), ("statistics", INT, REQ, 1.1),
            ("python", INT, REQ, 1.0), ("pandas", INT, REQ, 1.0),
            ("power-bi", INT, PREF, 0.9), ("tableau", BEG, PREF, 0.8),
            ("communication", ADV, REQ, 1.2), ("business-analysis", INT, PREF, 0.8),
            ("critical-thinking", INT, REQ, 0.9),
        ],
    },
    "data-engineer": {
        "title": "Data Engineer", "family": "Data & AI", "seniority": "ENTRY",
        "salary": (750000, 1800000), "demand": 85,
        "description": "Builds the pipelines and stores that everyone else's data work "
                       "depends on.",
        "responsibilities": [
            "Design and operate batch and streaming pipelines",
            "Model warehouses for analytics workloads",
            "Guarantee data quality, lineage and freshness",
        ],
        "skills": [
            ("python", ADV, REQ, 1.3), ("sql", EXP, REQ, 1.5),
            ("etl", ADV, REQ, 1.3), ("database-design", ADV, REQ, 1.2),
            ("spark", INT, REQ, 1.1), ("postgresql", INT, REQ, 1.0),
            ("docker", INT, REQ, 0.9), ("aws", INT, PREF, 0.9),
            ("message-queues", INT, PREF, 0.8), ("query-optimization", INT, REQ, 1.0),
            ("problem-solving", ADV, REQ, 0.9),
        ],
    },
    "devops-engineer": {
        "title": "DevOps Engineer", "family": "Infrastructure", "seniority": "ENTRY",
        "salary": (700000, 1800000), "demand": 87,
        "description": "Automates delivery so teams can ship safely and often.",
        "responsibilities": [
            "Own CI/CD pipelines and release automation",
            "Manage infrastructure as code",
            "Run monitoring, alerting and incident response",
        ],
        "skills": [
            ("linux", ADV, REQ, 1.3), ("docker", ADV, REQ, 1.4),
            ("ci-cd", ADV, REQ, 1.4), ("kubernetes", INT, REQ, 1.2),
            ("git", ADV, REQ, 1.0), ("shell-scripting", ADV, REQ, 1.1),
            ("aws", INT, REQ, 1.2), ("terraform", INT, REQ, 1.1),
            ("observability", INT, REQ, 1.0), ("nginx", INT, PREF, 0.8),
            ("python", INT, PREF, 0.8), ("ownership", ADV, REQ, 0.9),
        ],
    },
    "cloud-engineer": {
        "title": "Cloud Engineer", "family": "Infrastructure", "seniority": "ENTRY",
        "salary": (750000, 1900000), "demand": 84,
        "description": "Designs and operates secure, cost-effective cloud infrastructure.",
        "responsibilities": [
            "Architect cloud workloads for reliability and cost",
            "Automate provisioning with infrastructure as code",
            "Implement cloud security and access controls",
        ],
        "skills": [
            ("aws", ADV, REQ, 1.5), ("cloud-architecture", ADV, REQ, 1.3),
            ("linux", INT, REQ, 1.1), ("terraform", INT, REQ, 1.2),
            ("docker", INT, REQ, 1.0), ("networking-fundamentals", None, None, None),
            ("iam", INT, REQ, 1.0), ("ci-cd", INT, REQ, 1.0),
            ("kubernetes", BEG, PREF, 0.8), ("azure", BEG, PREF, 0.7),
            ("observability", INT, PREF, 0.8), ("problem-solving", ADV, REQ, 0.9),
        ],
    },
    "sre": {
        "title": "Site Reliability Engineer", "family": "Infrastructure", "seniority": "MID",
        "salary": (1000000, 2400000), "demand": 78,
        "description": "Applies software engineering to operations: reliability, "
                       "capacity and toil reduction.",
        "responsibilities": [
            "Define and defend SLOs",
            "Automate away operational toil",
            "Lead incident response and blameless postmortems",
        ],
        "skills": [
            ("linux", EXP, REQ, 1.4), ("kubernetes", ADV, REQ, 1.3),
            ("observability", ADV, REQ, 1.3), ("python", INT, REQ, 1.1),
            ("ci-cd", ADV, REQ, 1.1), ("system-design", ADV, REQ, 1.2),
            ("shell-scripting", ADV, REQ, 1.0), ("terraform", INT, PREF, 0.9),
            ("aws", INT, REQ, 1.0), ("problem-solving", EXP, REQ, 1.1),
            ("communication", ADV, REQ, 0.9),
        ],
    },
    "cybersecurity-analyst": {
        "title": "Cybersecurity Analyst", "family": "Security", "seniority": "ENTRY",
        "salary": (600000, 1600000), "demand": 83,
        "description": "Detects, investigates and responds to security threats.",
        "responsibilities": [
            "Monitor alerts and triage security incidents",
            "Run vulnerability assessments and track remediation",
            "Harden systems against the OWASP Top 10",
        ],
        "skills": [
            ("network-security", ADV, REQ, 1.3), ("owasp", ADV, REQ, 1.3),
            ("incident-response", INT, REQ, 1.2), ("siem", INT, REQ, 1.2),
            ("linux", INT, REQ, 1.0), ("cryptography", INT, REQ, 1.0),
            ("penetration-testing", INT, PREF, 1.0), ("iam", INT, REQ, 1.0),
            ("python", BEG, PREF, 0.7), ("application-security", INT, REQ, 1.1),
            ("critical-thinking", ADV, REQ, 1.0),
        ],
    },
    "application-security-engineer": {
        "title": "Application Security Engineer", "family": "Security", "seniority": "MID",
        "salary": (900000, 2200000), "demand": 75,
        "description": "Builds security into the SDLC and reviews code for weaknesses.",
        "responsibilities": [
            "Threat model new features",
            "Review code and dependencies for vulnerabilities",
            "Automate security testing in CI",
        ],
        "skills": [
            ("application-security", ADV, REQ, 1.5), ("owasp", ADV, REQ, 1.3),
            ("python", INT, REQ, 1.0), ("cryptography", INT, REQ, 1.0),
            ("penetration-testing", INT, REQ, 1.1), ("ci-cd", INT, REQ, 0.9),
            ("rest-api", INT, REQ, 0.9), ("iam", INT, REQ, 1.0),
            ("communication", INT, REQ, 0.8),
        ],
    },
    "qa-engineer": {
        "title": "QA Engineer", "family": "Engineering", "seniority": "ENTRY",
        "salary": (450000, 1100000), "demand": 74,
        "description": "Protects quality through thoughtful testing and automation.",
        "responsibilities": [
            "Design and execute test plans",
            "Automate regression suites",
            "Report and triage defects with clear reproduction steps",
        ],
        "skills": [
            ("manual-testing", ADV, REQ, 1.3), ("test-automation", ADV, REQ, 1.3),
            ("selenium", INT, REQ, 1.1), ("sql", INT, REQ, 0.9),
            ("unit-testing", INT, REQ, 1.0), ("playwright", INT, PREF, 0.9),
            ("git", INT, REQ, 0.9), ("python", BEG, PREF, 0.7),
            ("jira", INT, REQ, 0.8), ("critical-thinking", ADV, REQ, 1.0),
            ("communication", INT, REQ, 0.9),
        ],
    },
    "ui-ux-designer": {
        "title": "UI/UX Designer", "family": "Design", "seniority": "ENTRY",
        "salary": (500000, 1400000), "demand": 76,
        "description": "Designs interfaces people understand at a glance, grounded in "
                       "real user research.",
        "responsibilities": [
            "Run user research and synthesise findings",
            "Produce wireframes, prototypes and high-fidelity designs",
            "Maintain and extend the design system",
        ],
        "skills": [
            ("figma", ADV, REQ, 1.4), ("ui-design", ADV, REQ, 1.4),
            ("ux-research", ADV, REQ, 1.3), ("wireframing", ADV, REQ, 1.2),
            ("design-systems", INT, REQ, 1.0), ("interaction-design", INT, PREF, 0.9),
            ("web-accessibility", INT, REQ, 1.0), ("html", BEG, PREF, 0.6),
            ("communication", ADV, REQ, 1.1), ("customer-focus", ADV, REQ, 1.0),
            ("presentation", INT, REQ, 0.9),
        ],
    },
    "product-manager": {
        "title": "Product Manager", "family": "Product", "seniority": "ENTRY",
        "salary": (900000, 2400000), "demand": 80,
        "description": "Decides what to build and why, then makes it happen with the team.",
        "responsibilities": [
            "Own the product roadmap and its rationale",
            "Write clear specifications and success metrics",
            "Align engineering, design and business stakeholders",
        ],
        "skills": [
            ("product-management", ADV, REQ, 1.5), ("agile", ADV, REQ, 1.2),
            ("roadmapping", ADV, REQ, 1.2), ("stakeholder-management", ADV, REQ, 1.2),
            ("requirements-gathering", ADV, REQ, 1.1), ("product-analytics", INT, REQ, 1.1),
            ("communication", EXP, REQ, 1.4), ("market-research", INT, PREF, 0.8),
            ("sql", BEG, PREF, 0.7), ("critical-thinking", ADV, REQ, 1.1),
            ("presentation", ADV, REQ, 1.0), ("leadership", INT, REQ, 1.0),
        ],
    },
    "business-analyst": {
        "title": "Business Analyst", "family": "Product", "seniority": "ENTRY",
        "salary": (500000, 1300000), "demand": 77,
        "description": "Bridges business need and technical delivery with precise "
                       "requirements.",
        "responsibilities": [
            "Elicit and document requirements",
            "Map as-is and to-be processes",
            "Support UAT and change management",
        ],
        "skills": [
            ("business-analysis", ADV, REQ, 1.5), ("requirements-gathering", ADV, REQ, 1.4),
            ("sql", INT, REQ, 1.1), ("excel", ADV, REQ, 1.1),
            ("stakeholder-management", ADV, REQ, 1.2), ("jira", INT, REQ, 0.9),
            ("data-visualization", INT, PREF, 0.8), ("agile", INT, REQ, 1.0),
            ("communication", ADV, REQ, 1.3), ("presentation", INT, REQ, 0.9),
        ],
    },
    "mobile-developer": {
        "title": "Mobile App Developer", "family": "Engineering", "seniority": "ENTRY",
        "salary": (600000, 1500000), "demand": 73,
        "description": "Builds mobile applications people use every day.",
        "responsibilities": [
            "Build and ship mobile features",
            "Optimise app performance and battery use",
            "Manage store releases and crash triage",
        ],
        "skills": [
            ("flutter", ADV, REQ, 1.3), ("react-native", INT, PREF, 1.0),
            ("javascript", INT, REQ, 1.0), ("rest-api", INT, REQ, 1.1),
            ("git", INT, REQ, 0.9), ("android", INT, REQ, 1.1),
            ("ios", BEG, PREF, 0.8), ("unit-testing", BEG, PREF, 0.7),
            ("problem-solving", INT, REQ, 0.9),
        ],
    },
    "android-developer": {
        "title": "Android Developer", "family": "Engineering", "seniority": "ENTRY",
        "salary": (600000, 1500000), "demand": 70,
        "description": "Specialises in native Android applications.",
        "responsibilities": [
            "Build Android features with Kotlin and Jetpack",
            "Integrate APIs and local persistence",
            "Ship to the Play Store and monitor stability",
        ],
        "skills": [
            ("android", ADV, REQ, 1.5), ("kotlin", ADV, REQ, 1.4),
            ("java", INT, REQ, 1.0), ("rest-api", INT, REQ, 1.1),
            ("git", INT, REQ, 0.9), ("unit-testing", INT, PREF, 0.8),
            ("problem-solving", INT, REQ, 0.9),
        ],
    },
    "ios-developer": {
        "title": "iOS Developer", "family": "Engineering", "seniority": "ENTRY",
        "salary": (650000, 1600000), "demand": 62,
        "description": "Specialises in native iOS applications.",
        "responsibilities": [
            "Build iOS features with Swift and SwiftUI",
            "Integrate APIs and handle offline state",
            "Manage App Store releases",
        ],
        "skills": [
            ("ios", ADV, REQ, 1.5), ("swift", ADV, REQ, 1.4),
            ("rest-api", INT, REQ, 1.1), ("git", INT, REQ, 0.9),
            ("unit-testing", INT, PREF, 0.8), ("problem-solving", INT, REQ, 0.9),
        ],
    },
    "solutions-architect": {
        "title": "Solutions Architect", "family": "Engineering", "seniority": "SENIOR",
        "salary": (1800000, 4000000), "demand": 68,
        "description": "Designs systems that meet business goals within real constraints.",
        "responsibilities": [
            "Produce architecture decisions and trade-off analyses",
            "Set technical standards across teams",
            "Advise stakeholders on cost, risk and sequencing",
        ],
        "skills": [
            ("system-design", EXP, REQ, 1.5), ("cloud-architecture", ADV, REQ, 1.3),
            ("microservices", ADV, REQ, 1.2), ("aws", ADV, REQ, 1.2),
            ("database-design", ADV, REQ, 1.1), ("rest-api", ADV, REQ, 1.0),
            ("communication", ADV, REQ, 1.2), ("leadership", ADV, REQ, 1.1),
            ("stakeholder-management", ADV, REQ, 1.0),
        ],
    },
    "database-administrator": {
        "title": "Database Administrator", "family": "Infrastructure", "seniority": "MID",
        "salary": (700000, 1700000), "demand": 60,
        "description": "Keeps data available, fast and safe.",
        "responsibilities": [
            "Tune queries, indexes and configuration",
            "Run backup, restore and disaster recovery drills",
            "Manage access control and auditing",
        ],
        "skills": [
            ("postgresql", EXP, REQ, 1.5), ("sql", EXP, REQ, 1.4),
            ("query-optimization", ADV, REQ, 1.3), ("database-design", ADV, REQ, 1.2),
            ("linux", INT, REQ, 1.0), ("mysql", INT, PREF, 0.8),
            ("shell-scripting", INT, PREF, 0.8), ("observability", INT, PREF, 0.8),
        ],
    },
    "network-engineer": {
        "title": "Network Engineer", "family": "Infrastructure", "seniority": "ENTRY",
        "salary": (450000, 1200000), "demand": 58,
        "description": "Designs and operates reliable, secure networks.",
        "responsibilities": [
            "Configure and troubleshoot network infrastructure",
            "Implement segmentation and access policy",
            "Monitor capacity and availability",
        ],
        "skills": [
            ("network-security", ADV, REQ, 1.4), ("linux", INT, REQ, 1.1),
            ("nginx", INT, PREF, 0.8), ("observability", INT, REQ, 1.0),
            ("shell-scripting", INT, REQ, 0.9), ("problem-solving", ADV, REQ, 1.0),
        ],
    },
    "embedded-engineer": {
        "title": "Embedded Systems Engineer", "family": "Engineering", "seniority": "ENTRY",
        "salary": (550000, 1400000), "demand": 56,
        "description": "Writes software that runs close to the hardware.",
        "responsibilities": [
            "Develop firmware for microcontrollers",
            "Debug with oscilloscopes and logic analysers",
            "Optimise for memory and power constraints",
        ],
        "skills": [
            ("c-language", EXP, REQ, 1.5), ("c-plus-plus", ADV, REQ, 1.3),
            ("linux", INT, REQ, 1.0), ("git", INT, REQ, 0.9),
            ("problem-solving", ADV, REQ, 1.1), ("python", BEG, PREF, 0.6),
        ],
    },
    "research-engineer": {
        "title": "Research Engineer", "family": "Data & AI", "seniority": "MID",
        "salary": (1200000, 3000000), "demand": 62,
        "description": "Turns research ideas into working systems and rigorous results.",
        "responsibilities": [
            "Implement and reproduce research methods",
            "Design experiments with sound baselines",
            "Publish and present findings",
        ],
        "skills": [
            ("python", ADV, REQ, 1.3), ("deep-learning", ADV, REQ, 1.4),
            ("pytorch", ADV, REQ, 1.3), ("statistics", ADV, REQ, 1.2),
            ("machine-learning", ADV, REQ, 1.2), ("critical-thinking", EXP, REQ, 1.2),
            ("presentation", INT, REQ, 0.9), ("responsible-ai", INT, PREF, 0.8),
        ],
    },
    "technical-writer": {
        "title": "Technical Writer", "family": "Product", "seniority": "ENTRY",
        "salary": (450000, 1200000), "demand": 52,
        "description": "Makes complex systems understandable in writing.",
        "responsibilities": [
            "Write and maintain developer documentation",
            "Create tutorials and API references",
            "Work with engineers to keep docs accurate",
        ],
        "skills": [
            ("communication", EXP, REQ, 1.5), ("git", INT, REQ, 1.0),
            ("rest-api", INT, REQ, 1.0), ("critical-thinking", ADV, REQ, 1.0),
            ("html", BEG, PREF, 0.6), ("python", BEG, PREF, 0.6),
        ],
    },
    "devrel-engineer": {
        "title": "Developer Advocate", "family": "Product", "seniority": "MID",
        "salary": (1000000, 2400000), "demand": 50,
        "description": "Helps developers succeed with a product, publicly.",
        "responsibilities": [
            "Build demos and sample applications",
            "Speak at events and write technical content",
            "Carry developer feedback back to product",
        ],
        "skills": [
            ("communication", EXP, REQ, 1.4), ("presentation", ADV, REQ, 1.3),
            ("python", INT, REQ, 1.0), ("javascript", INT, REQ, 1.0),
            ("rest-api", ADV, REQ, 1.1), ("customer-focus", ADV, REQ, 1.1),
            ("git", INT, REQ, 0.9),
        ],
    },
    "game-developer": {
        "title": "Game Developer", "family": "Engineering", "seniority": "ENTRY",
        "salary": (450000, 1300000), "demand": 48,
        "description": "Builds interactive real-time experiences.",
        "responsibilities": [
            "Implement gameplay systems",
            "Optimise frame time and memory",
            "Collaborate with artists and designers",
        ],
        "skills": [
            ("c-plus-plus", ADV, REQ, 1.4), ("csharp", INT, REQ, 1.1),
            ("problem-solving", ADV, REQ, 1.1), ("git", INT, REQ, 0.9),
            ("computer-vision", BEG, PREF, 0.5), ("teamwork", INT, REQ, 0.9),
        ],
    },
    "blockchain-developer": {
        "title": "Blockchain Developer", "family": "Engineering", "seniority": "MID",
        "salary": (900000, 2400000), "demand": 46,
        "description": "Builds decentralised applications and smart contracts.",
        "responsibilities": [
            "Write and audit smart contracts",
            "Integrate on-chain data with application backends",
            "Optimise gas and transaction cost",
        ],
        "skills": [
            ("javascript", ADV, REQ, 1.2), ("rust", INT, PREF, 0.9),
            ("cryptography", ADV, REQ, 1.3), ("rest-api", INT, REQ, 1.0),
            ("system-design", INT, REQ, 1.0), ("application-security", INT, REQ, 1.1),
        ],
    },
}

# Remove the accidental placeholder entry defensively (kept explicit so the
# data file stays honest about what it contains).
for _role in JOB_ROLES.values():
    _role["skills"] = [s for s in _role["skills"] if s[1] is not None]


def skill_slugs() -> set[str]:
    return {s[0] for s in SKILLS}


def validate() -> list[str]:
    """Return a list of referential problems in the catalogue (used by tests)."""
    problems: list[str] = []
    categories = {c[0] for c in CATEGORIES}
    slugs = skill_slugs()
    if len(slugs) != len(SKILLS):
        problems.append("duplicate skill slugs")
    for slug, _name, category, *_ in SKILLS:
        if category not in categories:
            problems.append(f"skill {slug} references unknown category {category}")
    for role_slug, role in JOB_ROLES.items():
        if not role["skills"]:
            problems.append(f"role {role_slug} has no skills")
        for skill_slug, *_ in role["skills"]:
            if skill_slug not in slugs:
                problems.append(f"role {role_slug} references unknown skill {skill_slug}")
    return problems
