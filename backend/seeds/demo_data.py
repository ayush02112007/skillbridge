"""Static definitions for the demo dataset.

Everything produced from this file is flagged ``is_demo=True`` in the database
and is clearly labelled in the UI. Companies, institutions, people and postings
here are fictional; any resemblance to real organisations is incidental and the
names are deliberately invented.
"""
from __future__ import annotations

INSTITUTIONS: list[dict] = [
    {
        "name": "Pune Institute of Technology",
        "short_name": "PIT",
        "city": "Pune", "state": "Maharashtra",
        "institution_type": "ENGINEERING_COLLEGE",
        "accreditation": "NAAC A+",
        "established_year": 1983,
        "description": "Engineering institute with a strong placement programme "
                       "and an active industry advisory board.",
        "departments": [
            ("Computer Engineering", "CSE"), ("Information Technology", "IT"),
            ("Electronics & Telecommunication", "ENTC"),
            ("Mechanical Engineering", "MECH"), ("Data Science", "DS"),
        ],
    },
    {
        "name": "Bengaluru University of Technology",
        "short_name": "BUT",
        "city": "Bengaluru", "state": "Karnataka",
        "institution_type": "UNIVERSITY",
        "accreditation": "NAAC A",
        "established_year": 1996,
        "description": "Technology university with dedicated AI and cybersecurity "
                       "centres of excellence.",
        "departments": [
            ("Computer Science & Engineering", "CSE"),
            ("Artificial Intelligence & ML", "AIML"),
            ("Cyber Security", "CYS"), ("Electrical Engineering", "EEE"),
        ],
    },
    {
        "name": "Delhi Institute of Engineering",
        "short_name": "DIE",
        "city": "New Delhi", "state": "Delhi",
        "institution_type": "ENGINEERING_COLLEGE",
        "accreditation": "NBA Accredited",
        "established_year": 1978,
        "description": "Long-established engineering college with a large "
                       "alumni network across product companies.",
        "departments": [
            ("Computer Science", "CS"), ("Information Technology", "IT"),
            ("Electronics Engineering", "ECE"),
        ],
    },
    {
        "name": "Chennai College of Science & Technology",
        "short_name": "CCST",
        "city": "Chennai", "state": "Tamil Nadu",
        "institution_type": "AUTONOMOUS_COLLEGE",
        "accreditation": "NAAC A",
        "established_year": 2001,
        "description": "Autonomous college focused on applied computing and "
                       "industry-linked capstone projects.",
        "departments": [
            ("Computer Science & Business Systems", "CSBS"),
            ("Information Science", "IS"), ("Software Engineering", "SE"),
        ],
    },
    {
        "name": "Hyderabad School of Computing",
        "short_name": "HSC",
        "city": "Hyderabad", "state": "Telangana",
        "institution_type": "DEEMED_UNIVERSITY",
        "accreditation": "NAAC A++",
        "established_year": 2008,
        "description": "Deemed university specialising in computing, data "
                       "science and product design.",
        "departments": [
            ("Computer Science", "CS"), ("Data Science & Analytics", "DSA"),
            ("Product Design", "PD"),
        ],
    },
]

COMPANIES: list[dict] = [
    {
        "name": "Nimbus Labs", "sector": "Cloud Infrastructure", "city": "Bengaluru",
        "employees": 850, "founded": 2014,
        "description": "Cloud-native infrastructure tooling for engineering teams.",
        "about": "Nimbus Labs builds the deployment and observability platform used "
                 "by mid-sized engineering organisations. We run a structured "
                 "internship programme with mentorship and real production work.",
        "tech": ["Python", "Go", "Kubernetes", "PostgreSQL", "AWS", "Terraform"],
        "benefits": ["Learning budget", "Hybrid working", "Mentor for every intern"],
    },
    {
        "name": "Meridian Analytics", "sector": "Data & AI", "city": "Pune",
        "employees": 420, "founded": 2017,
        "description": "Decision intelligence for retail and supply chain.",
        "about": "Meridian builds forecasting and optimisation systems. Our teams "
                 "pair data scientists with engineers from day one.",
        "tech": ["Python", "PyTorch", "Spark", "Airflow", "Snowflake"],
        "benefits": ["Conference sponsorship", "Research time", "Remote friendly"],
    },
    {
        "name": "Aegis Secure", "sector": "Cybersecurity", "city": "Hyderabad",
        "employees": 300, "founded": 2015,
        "description": "Managed detection and response for regulated industries.",
        "about": "Aegis Secure runs a 24/7 security operations centre and an "
                 "application security practice.",
        "tech": ["Python", "Splunk", "Linux", "Kubernetes", "Go"],
        "benefits": ["Certification sponsorship", "Shift allowance", "On-call rotation"],
    },
    {
        "name": "Orbit Commerce", "sector": "E-commerce", "city": "Bengaluru",
        "employees": 2400, "founded": 2011,
        "description": "Marketplace platform serving 14 million customers.",
        "about": "Orbit Commerce operates a high-traffic marketplace. Engineering "
                 "is organised into small teams owning services end to end.",
        "tech": ["Java", "Spring Boot", "React", "Kafka", "MySQL", "Redis"],
        "benefits": ["Relocation support", "Health cover", "Employee stock"],
    },
    {
        "name": "Lumen Health", "sector": "Health Technology", "city": "Chennai",
        "employees": 560, "founded": 2018,
        "description": "Clinical workflow software for hospital networks.",
        "about": "Lumen Health digitises clinical pathways. We care deeply about "
                 "accessibility, privacy and getting details right.",
        "tech": ["TypeScript", "Next.js", "Node.js", "PostgreSQL", "Azure"],
        "benefits": ["Flexible hours", "Wellness stipend", "Paid volunteering"],
    },
    {
        "name": "Terra Fintech", "sector": "Financial Services", "city": "Mumbai",
        "employees": 1100, "founded": 2013,
        "description": "Payments and lending infrastructure for small businesses.",
        "about": "Terra Fintech processes payments for over 200,000 merchants. "
                 "Reliability and correctness are the job.",
        "tech": ["Java", "Kotlin", "PostgreSQL", "Kafka", "AWS"],
        "benefits": ["Performance bonus", "Insurance", "Learning stipend"],
    },
    {
        "name": "Vertex Robotics", "sector": "Industrial Automation", "city": "Pune",
        "employees": 380, "founded": 2016,
        "description": "Warehouse automation and autonomous handling systems.",
        "about": "Vertex Robotics builds robots that move goods. Embedded, "
                 "computer vision and cloud, in one product.",
        "tech": ["C++", "Python", "ROS", "Computer Vision", "Docker"],
        "benefits": ["Hardware lab access", "Patent bonus", "Hybrid working"],
    },
    {
        "name": "Pixel Foundry", "sector": "Product Design", "city": "Bengaluru",
        "employees": 140, "founded": 2019,
        "description": "Product design studio for software companies.",
        "about": "Pixel Foundry designs interfaces for complex products. Research "
                 "first, pixels second.",
        "tech": ["Figma", "React", "TypeScript", "Design Systems"],
        "benefits": ["Design conference budget", "4-day sprint cycles"],
    },
    {
        "name": "Cardinal Consulting", "sector": "Technology Consulting", "city": "New Delhi",
        "employees": 3200, "founded": 2004,
        "description": "Enterprise technology consulting and managed services.",
        "about": "Cardinal Consulting delivers large modernisation programmes for "
                 "public and private sector clients.",
        "tech": ["Java", ".NET Core", "Azure", "SQL", "Power BI"],
        "benefits": ["Structured training", "Global mobility", "Certification support"],
    },
    {
        "name": "Solstice Energy", "sector": "Clean Energy", "city": "Ahmedabad",
        "employees": 700, "founded": 2012,
        "description": "Software for distributed renewable energy assets.",
        "about": "Solstice Energy monitors and optimises solar and wind assets "
                 "across three continents.",
        "tech": ["Python", "TimescaleDB", "React", "AWS", "IoT"],
        "benefits": ["Field visits", "Green commute allowance", "Hybrid working"],
    },
]

# (title, role slug, kind, city, work mode, stipend, duration weeks, description)
INTERNSHIPS: list[tuple] = [
    ("Backend Engineering Intern", "backend-developer", "Nimbus Labs", "Bengaluru", "HYBRID", (25000, 35000), 12,
     "Work on the API layer of our deployment platform. You will design and ship "
     "REST endpoints in Python and FastAPI, model data in PostgreSQL, and take part "
     "in code review. Docker is part of daily work. Familiarity with AWS is a plus."),
    ("Platform Engineering Intern", "devops-engineer", "Nimbus Labs", "Bengaluru", "ONSITE", (28000, 38000), 16,
     "Join the platform team building CI/CD pipelines and Kubernetes tooling. "
     "Strong Linux and Docker skills required. Terraform experience is desirable."),
    ("Data Science Intern", "data-scientist", "Meridian Analytics", "Pune", "HYBRID", (22000, 32000), 12,
     "Build forecasting models for retail demand. Requires Python, Pandas, "
     "scikit-learn and solid statistics. Experience with SQL is essential."),
    ("Machine Learning Intern", "ml-engineer", "Meridian Analytics", "Pune", "REMOTE", (25000, 35000), 16,
     "Take models from notebook to production. You will use Python, PyTorch and "
     "Docker, and help build our MLOps pipelines. Good to have: AWS."),
    ("Security Analyst Intern", "cybersecurity-analyst", "Aegis Secure", "Hyderabad", "ONSITE", (20000, 28000), 12,
     "Join our SOC and learn threat detection hands on. Requires understanding of "
     "network security, the OWASP Top 10 and Linux. Python scripting is a plus."),
    ("Application Security Intern", "application-security-engineer", "Aegis Secure", "Hyderabad", "HYBRID", (24000, 32000), 12,
     "Review code and dependencies for vulnerabilities. Requires application "
     "security fundamentals, OWASP knowledge and Python."),
    ("Full Stack Developer Intern", "full-stack-developer", "Orbit Commerce", "Bengaluru", "ONSITE", (30000, 40000), 24,
     "Own features end to end across React, Node.js and MySQL. You will work with "
     "REST APIs and Git daily. Java and Kafka exposure is a bonus."),
    ("Frontend Engineering Intern", "frontend-developer", "Orbit Commerce", "Bengaluru", "HYBRID", (26000, 34000), 12,
     "Build customer-facing interfaces in React and TypeScript. Strong JavaScript, "
     "HTML5 and CSS3 required. We care about web accessibility."),
    ("Frontend Intern (Healthcare UI)", "frontend-developer", "Lumen Health", "Chennai", "REMOTE", (20000, 28000), 12,
     "Build clinical interfaces in Next.js and TypeScript. Accessibility is a hard "
     "requirement, not a nice-to-have. Tailwind CSS experience helps."),
    ("Backend Intern (Clinical Systems)", "backend-developer", "Lumen Health", "Chennai", "HYBRID", (22000, 30000), 16,
     "Build services in Node.js and PostgreSQL with strict data-privacy rules. "
     "REST API design and unit testing are core to the role."),
    ("Payments Backend Intern", "java-developer", "Terra Fintech", "Mumbai", "ONSITE", (30000, 42000), 24,
     "Work on payment processing in Java and Spring Boot. Requires strong SQL and "
     "REST API skills. Kafka and Kubernetes exposure is desirable."),
    ("Quality Engineering Intern", "qa-engineer", "Terra Fintech", "Mumbai", "HYBRID", (18000, 26000), 12,
     "Design and automate test suites. Requires manual testing discipline, "
     "Selenium and SQL. Playwright experience is a plus."),
    ("Robotics Software Intern", "embedded-engineer", "Vertex Robotics", "Pune", "ONSITE", (24000, 34000), 24,
     "Write firmware and control software in C and C++. Linux and Git required. "
     "Python for tooling is useful."),
    ("Computer Vision Intern", "ml-engineer", "Vertex Robotics", "Pune", "ONSITE", (26000, 36000), 16,
     "Build perception pipelines. Requires Python, computer vision and deep "
     "learning fundamentals. PyTorch preferred."),
    ("Product Design Intern", "ui-ux-designer", "Pixel Foundry", "Bengaluru", "HYBRID", (20000, 28000), 12,
     "Run research, build prototypes and ship interfaces. Requires Figma, UI design "
     "and UX research. Design systems experience is a plus."),
    ("Business Analyst Intern", "business-analyst", "Cardinal Consulting", "New Delhi", "ONSITE", (18000, 25000), 12,
     "Gather requirements and map processes for modernisation programmes. Requires "
     "business analysis, SQL and advanced Excel. Strong communication essential."),
    ("Cloud Engineering Intern", "cloud-engineer", "Cardinal Consulting", "New Delhi", "HYBRID", (24000, 32000), 16,
     "Support cloud migrations on Azure and AWS. Requires cloud architecture "
     "fundamentals, Linux and Terraform."),
    ("Data Engineering Intern", "data-engineer", "Solstice Energy", "Ahmedabad", "REMOTE", (22000, 30000), 16,
     "Build pipelines for time-series energy data. Requires Python, strong SQL and "
     "ETL experience. Spark is desirable."),
    ("Analytics Intern", "data-analyst", "Solstice Energy", "Ahmedabad", "REMOTE", (16000, 22000), 12,
     "Turn asset telemetry into operational dashboards. Requires SQL, advanced "
     "Excel and data visualisation. Power BI is a plus."),
    ("AI Engineering Intern", "ai-engineer", "Meridian Analytics", "Pune", "REMOTE", (30000, 40000), 16,
     "Build retrieval-augmented applications on top of language models. Requires "
     "Python and LLM engineering fundamentals. Responsible AI practice matters here."),
]

JOBS: list[tuple] = [
    ("Backend Developer", "backend-developer", "Nimbus Labs", "Bengaluru", "HYBRID", (900000, 1500000), 0.0,
     "Design and operate the services behind our platform. You will write Python "
     "and FastAPI, design PostgreSQL schemas, and own your services in production "
     "with Docker and AWS. We expect strong REST API design and system design sense."),
    ("Site Reliability Engineer", "sre", "Nimbus Labs", "Bengaluru", "ONSITE", (1600000, 2600000), 2.0,
     "Own reliability for our platform. Deep Linux, Kubernetes and observability "
     "skills required, with Python for automation and Terraform for infrastructure."),
    ("Data Scientist", "data-scientist", "Meridian Analytics", "Pune", "HYBRID", (1200000, 2000000), 1.0,
     "Build and validate forecasting models. Requires Python, statistics, machine "
     "learning, Pandas and scikit-learn, plus the communication skills to explain "
     "results to business stakeholders."),
    ("Machine Learning Engineer", "ml-engineer", "Meridian Analytics", "Pune", "REMOTE", (1400000, 2400000), 2.0,
     "Productionise models and own their performance. Requires Python, machine "
     "learning, PyTorch, Docker and MLOps practice. Kubernetes is a plus."),
    ("Cybersecurity Analyst", "cybersecurity-analyst", "Aegis Secure", "Hyderabad", "ONSITE", (800000, 1400000), 1.0,
     "Monitor, triage and respond to security incidents. Requires network security, "
     "OWASP Top 10, SIEM tooling and incident response experience."),
    ("Application Security Engineer", "application-security-engineer", "Aegis Secure", "Hyderabad", "HYBRID", (1500000, 2500000), 3.0,
     "Build security into the SDLC. Requires application security, OWASP, "
     "cryptography, penetration testing and CI/CD integration."),
    ("Full Stack Developer", "full-stack-developer", "Orbit Commerce", "Bengaluru", "ONSITE", (1000000, 1800000), 1.0,
     "Ship features across React, Node.js and MySQL. Requires strong JavaScript, "
     "REST API design, SQL and Docker. TypeScript preferred."),
    ("Frontend Developer", "frontend-developer", "Orbit Commerce", "Bengaluru", "HYBRID", (900000, 1600000), 1.0,
     "Build and optimise our customer interfaces. Requires JavaScript, React, "
     "TypeScript, HTML5, CSS3 and state management. Accessibility matters."),
    ("Senior Frontend Engineer", "frontend-developer", "Lumen Health", "Chennai", "REMOTE", (1600000, 2600000), 4.0,
     "Lead frontend architecture for clinical products. Requires deep React and "
     "TypeScript, Next.js, and genuine web accessibility expertise."),
    ("Java Developer", "java-developer", "Terra Fintech", "Mumbai", "ONSITE", (1100000, 1900000), 1.0,
     "Build payment services in Java and Spring Boot. Requires strong SQL, REST API "
     "design and unit testing. Microservices and Docker experience preferred."),
    ("QA Engineer", "qa-engineer", "Terra Fintech", "Mumbai", "HYBRID", (700000, 1200000), 1.0,
     "Own quality for payment flows. Requires test automation, Selenium, SQL and "
     "manual testing discipline. Playwright is a plus."),
    ("Embedded Systems Engineer", "embedded-engineer", "Vertex Robotics", "Pune", "ONSITE", (1000000, 1800000), 2.0,
     "Write firmware for autonomous handling systems. Requires C, C++, Linux and "
     "strong debugging skills."),
    ("UI/UX Designer", "ui-ux-designer", "Pixel Foundry", "Bengaluru", "HYBRID", (900000, 1600000), 2.0,
     "Design interfaces grounded in research. Requires Figma, UI design, UX "
     "research, wireframing and design systems experience."),
    ("Product Manager", "product-manager", "Pixel Foundry", "Bengaluru", "HYBRID", (1800000, 3000000), 3.0,
     "Own product direction for a design-tooling line. Requires product management, "
     "agile delivery, roadmapping, stakeholder management and excellent communication."),
    ("Business Analyst", "business-analyst", "Cardinal Consulting", "New Delhi", "ONSITE", (700000, 1300000), 1.0,
     "Elicit requirements and shape delivery for enterprise clients. Requires "
     "business analysis, requirements gathering, SQL and advanced Excel."),
    ("Cloud Engineer", "cloud-engineer", "Cardinal Consulting", "New Delhi", "HYBRID", (1200000, 2100000), 2.0,
     "Design and run cloud workloads. Requires AWS, cloud architecture, Terraform, "
     "Linux and identity and access management."),
    ("Data Engineer", "data-engineer", "Solstice Energy", "Ahmedabad", "REMOTE", (1100000, 1900000), 2.0,
     "Build the pipelines behind our analytics. Requires Python, expert SQL, ETL, "
     "database design and query optimisation. Spark preferred."),
    ("Data Analyst", "data-analyst", "Solstice Energy", "Ahmedabad", "REMOTE", (600000, 1100000), 0.0,
     "Answer operational questions with data. Requires SQL, advanced Excel, data "
     "visualisation and clear communication. Power BI is a plus."),
    ("DevOps Engineer", "devops-engineer", "Orbit Commerce", "Bengaluru", "HYBRID", (1200000, 2200000), 2.0,
     "Own delivery pipelines and infrastructure. Requires Linux, Docker, CI/CD, "
     "Kubernetes, Git and AWS. Terraform and observability experience preferred."),
    ("AI Engineer", "ai-engineer", "Nimbus Labs", "Bengaluru", "REMOTE", (1800000, 3000000), 2.0,
     "Build model-backed product features. Requires Python, LLM engineering, NLP "
     "fundamentals, REST API design and responsible AI practice."),
]

LIVE_PROJECTS: list[tuple] = [
    ("Open-source Kubernetes cost dashboard", "Nimbus Labs", "Bengaluru", 8, (2, 4),
     "Build a dashboard that attributes Kubernetes spend to teams and services.",
     "A working dashboard with documented setup, deployed to a demo cluster."),
    ("Demand forecasting for regional retail", "Meridian Analytics", "Pune", 10, (2, 3),
     "Forecast weekly demand for 40 product lines using two years of history.",
     "A validated model, an error analysis, and a short written recommendation."),
    ("Phishing detection classifier", "Aegis Secure", "Hyderabad", 8, (2, 4),
     "Train and evaluate a classifier for phishing emails on a labelled corpus.",
     "A reproducible pipeline with precision/recall analysis and a threat writeup."),
    ("Accessible appointment booking flow", "Lumen Health", "Chennai", 6, (2, 3),
     "Redesign and build an appointment flow that meets WCAG AA.",
     "A tested, accessible implementation with an audit report."),
    ("Merchant onboarding automation", "Terra Fintech", "Mumbai", 12, (3, 5),
     "Automate document checks in merchant onboarding.",
     "A service with an API, tests and a measured reduction in manual steps."),
]

EVENTS: list[tuple] = [
    ("Building Production APIs with FastAPI", "WORKSHOP", "Nimbus Labs", 14, 180,
     ["Python", "FastAPI", "REST API Design"],
     "A hands-on workshop taking a service from first endpoint to deployed container."),
    ("From Notebook to Production ML", "WEBINAR", "Meridian Analytics", 21, 90,
     ["Machine Learning", "MLOps", "Docker"],
     "How models actually reach users, and what breaks on the way."),
    ("OWASP Top 10 in Practice", "WORKSHOP", "Aegis Secure", 10, 150,
     ["OWASP Top 10", "Application Security"],
     "Exploit and then fix each class of vulnerability in a deliberately broken app."),
    ("Designing for Accessibility", "GUEST_LECTURE", "Lumen Health", 18, 90,
     ["Web Accessibility", "UI Design"],
     "Why accessibility is an engineering requirement, with live screen-reader demos."),
    ("Scaling Payments: An Architecture Deep Dive", "GUEST_LECTURE", "Terra Fintech", 25, 120,
     ["System Design", "Microservices"],
     "How a payment platform stays correct under load."),
    ("Campus Hackathon: Industry Challenge", "HACKATHON", "Orbit Commerce", 30, 2880,
     ["Problem Solving", "Teamwork"],
     "A 48-hour hackathon on real marketplace problems, judged by engineers."),
    ("Careers in Data: What Hiring Managers Look For", "CAREER_SESSION", "Meridian Analytics", 12, 60,
     ["Communication", "Statistics"],
     "An honest look at how data roles are actually filled."),
    ("Cloud Cost Engineering", "WEBINAR", "Cardinal Consulting", 16, 75,
     ["AWS", "Cloud Architecture"],
     "Practical techniques for reducing cloud spend without reducing reliability."),
    ("Robotics Open Lab", "INDUSTRY_VISIT", "Vertex Robotics", 20, 240,
     ["C++", "Computer Vision"],
     "A guided visit through our robotics lab and test floor."),
    ("Design Systems That Survive Contact With Engineering", "PANEL_DISCUSSION", "Pixel Foundry", 28, 90,
     ["Design Systems", "UI Design"],
     "Designers and engineers discuss what makes a design system stick."),
]

PROGRAMS: list[tuple] = [
    ("Python for Backend Engineering", "COURSE", "Nimbus Labs", "MEDIUM", 24, True,
     ["python", "fastapi", "rest-api"],
     "A practical course covering idiomatic Python, API design and testing."),
    ("PostgreSQL Performance Essentials", "COURSE", "Nimbus Labs", "HARD", 16, True,
     ["postgresql", "sql", "query-optimization"],
     "Indexing, query plans and the habits that keep a database fast."),
    ("Containers and CI/CD Foundations", "BOOTCAMP", "Nimbus Labs", "MEDIUM", 32, False,
     ["docker", "ci-cd", "kubernetes", "linux"],
     "Build, ship and operate containerised services with automated pipelines."),
    ("Applied Machine Learning", "CERTIFICATION", "Meridian Analytics", "HARD", 40, False,
     ["machine-learning", "scikit-learn", "pandas", "statistics"],
     "End-to-end supervised learning with rigorous evaluation."),
    ("Deep Learning with PyTorch", "COURSE", "Meridian Analytics", "HARD", 36, False,
     ["deep-learning", "pytorch", "python"],
     "Neural network fundamentals through to training real models."),
    ("Building LLM Applications", "WORKSHOP", "Meridian Analytics", "MEDIUM", 12, True,
     ["llm-engineering", "nlp", "responsible-ai"],
     "Retrieval, orchestration, evaluation and safety for model-backed products."),
    ("Secure Coding Practices", "CERTIFICATION", "Aegis Secure", "MEDIUM", 20, True,
     ["application-security", "owasp", "cryptography"],
     "Write code that resists the attacks that actually happen."),
    ("SOC Analyst Fundamentals", "TRAINING", "Aegis Secure", "MEDIUM", 28, False,
     ["siem", "incident-response", "network-security", "linux"],
     "Detection, triage and response, practised on realistic incident data."),
    ("Modern React and TypeScript", "COURSE", "Orbit Commerce", "MEDIUM", 28, True,
     ["react", "typescript", "javascript", "redux"],
     "Component design, state management and performance in production React."),
    ("Frontend Accessibility Certification", "CERTIFICATION", "Lumen Health", "MEDIUM", 14, True,
     ["web-accessibility", "html", "css"],
     "WCAG in practice, including testing with assistive technology."),
    ("Next.js in Production", "COURSE", "Lumen Health", "MEDIUM", 18, True,
     ["nextjs", "react", "typescript"],
     "Rendering strategies, data fetching and deployment for Next.js apps."),
    ("Java Microservices with Spring Boot", "COURSE", "Terra Fintech", "HARD", 34, False,
     ["java", "spring-boot", "microservices", "rest-api"],
     "Design, build and operate services on the JVM."),
    ("Test Automation Practitioner", "CERTIFICATION", "Terra Fintech", "MEDIUM", 22, True,
     ["test-automation", "selenium", "playwright", "unit-testing"],
     "Build a regression suite that teams actually trust."),
    ("C++ for Embedded Systems", "COURSE", "Vertex Robotics", "HARD", 30, False,
     ["c-plus-plus", "c-language", "linux"],
     "Memory, timing and debugging on constrained hardware."),
    ("Computer Vision Fundamentals", "COURSE", "Vertex Robotics", "HARD", 26, False,
     ["computer-vision", "python", "deep-learning"],
     "From classical techniques to modern detection models."),
    ("Product Design Intensive", "BOOTCAMP", "Pixel Foundry", "MEDIUM", 40, False,
     ["figma", "ui-design", "ux-research", "wireframing"],
     "Research through to high-fidelity design, with critique throughout."),
    ("Design Systems Masterclass", "WORKSHOP", "Pixel Foundry", "MEDIUM", 10, True,
     ["design-systems", "figma", "ui-design"],
     "Building component libraries that scale across teams."),
    ("Business Analysis Essentials", "COURSE", "Cardinal Consulting", "EASY", 18, True,
     ["business-analysis", "requirements-gathering", "stakeholder-management"],
     "Turning ambiguous business need into buildable requirements."),
    ("AWS Cloud Practitioner Path", "CERTIFICATION", "Cardinal Consulting", "EASY", 20, True,
     ["aws", "cloud-architecture", "iam"],
     "Core AWS services and the well-architected principles behind them."),
    ("Data Engineering with Python", "COURSE", "Solstice Energy", "HARD", 32, False,
     ["etl", "python", "sql", "spark"],
     "Batch and streaming pipelines, data quality and orchestration."),
    ("SQL for Analysts", "COURSE", "Solstice Energy", "EASY", 14, True,
     ["sql", "data-visualization", "excel"],
     "Query, aggregate and communicate findings with confidence."),
    ("Communicating Technical Work", "WORKSHOP", "Cardinal Consulting", "EASY", 8, True,
     ["communication", "presentation", "critical-thinking"],
     "Explaining complex work to people who need to act on it."),
]

RESEARCH_PROJECTS: list[tuple] = [
    ("Federated learning for privacy-preserving retail forecasting", "RESEARCH",
     "Meridian Analytics", ["Machine Learning", "Privacy", "Distributed Systems"], 1800000, 18),
    ("Automated vulnerability triage using program analysis", "SPONSORED_RESEARCH",
     "Aegis Secure", ["Application Security", "Static Analysis"], 1200000, 12),
    ("Energy forecasting for distributed solar assets", "RESEARCH",
     "Solstice Energy", ["Time Series", "Renewable Energy", "Machine Learning"], 950000, 12),
    ("Consultancy: legacy modernisation assessment framework", "CONSULTANCY",
     "Cardinal Consulting", ["Software Architecture", "Enterprise Systems"], 600000, 6),
    ("Human factors in clinical interface design", "JOINT_PUBLICATION",
     "Lumen Health", ["Human-Computer Interaction", "Accessibility"], 400000, 9),
    ("Robust perception for warehouse robotics", "RESEARCH",
     "Vertex Robotics", ["Computer Vision", "Robotics"], 1500000, 24),
]

FACULTY_PROGRAMMES: list[tuple] = [
    ("Faculty Development Programme: Cloud-Native Architecture", "FDP", "Nimbus Labs", 5,
     ["Cloud Architecture", "Kubernetes", "DevOps"],
     "A five-day FDP for faculty teaching systems and cloud subjects."),
    ("Industry Immersion: Applied Machine Learning", "FACULTY_INTERNSHIP", "Meridian Analytics", 30,
     ["Machine Learning", "MLOps", "Data Engineering"],
     "A month-long placement working alongside our data science team."),
    ("Security Curriculum Workshop", "INDUSTRIAL_TRAINING", "Aegis Secure", 3,
     ["Application Security", "Incident Response"],
     "Helping departments build a credible security curriculum."),
    ("Consultancy Panel: Digital Health Standards", "CONSULTANCY", "Lumen Health", 10,
     ["Health Informatics", "Standards", "Accessibility"],
     "Paid consultancy engagement for faculty with relevant domain expertise."),
    ("Joint Research Call: Payments Reliability", "RESEARCH_COLLABORATION", "Terra Fintech", 90,
     ["Distributed Systems", "Reliability Engineering"],
     "An open call for research collaboration on payment system reliability."),
    ("Guest Lecture Series: Robotics in Industry", "GUEST_LECTURE", "Vertex Robotics", 1,
     ["Robotics", "Computer Vision"],
     "Invited lectures delivered at partner institutions."),
]

# Student archetypes: (skill slugs with levels, interests, target role slug)
STUDENT_ARCHETYPES: list[dict] = [
    {
        "name": "backend",
        "target": "backend-developer",
        "interests": ["Backend Development", "Cloud"],
        "roles": ["Backend Developer", "Full Stack Developer"],
        "skills": {
            "python": "ADVANCED", "sql": "INTERMEDIATE", "postgresql": "INTERMEDIATE",
            "rest-api": "INTERMEDIATE", "git": "INTERMEDIATE", "docker": "BEGINNER",
            "fastapi": "BEGINNER", "problem-solving": "ADVANCED",
            "communication": "INTERMEDIATE",
        },
    },
    {
        "name": "frontend",
        "target": "frontend-developer",
        "interests": ["Frontend Development", "Product Design"],
        "roles": ["Frontend Developer"],
        "skills": {
            "javascript": "ADVANCED", "react": "INTERMEDIATE", "html": "ADVANCED",
            "css": "ADVANCED", "git": "INTERMEDIATE", "typescript": "BEGINNER",
            "responsive-design": "INTERMEDIATE", "teamwork": "ADVANCED",
        },
    },
    {
        "name": "data",
        "target": "data-scientist",
        "interests": ["Data Science", "Artificial Intelligence"],
        "roles": ["Data Scientist", "Data Analyst"],
        "skills": {
            "python": "INTERMEDIATE", "statistics": "INTERMEDIATE", "pandas": "INTERMEDIATE",
            "numpy": "INTERMEDIATE", "sql": "INTERMEDIATE", "scikit-learn": "BEGINNER",
            "data-visualization": "INTERMEDIATE", "critical-thinking": "ADVANCED",
        },
    },
    {
        "name": "ml",
        "target": "ml-engineer",
        "interests": ["Artificial Intelligence", "Machine Learning"],
        "roles": ["Machine Learning Engineer", "AI Engineer"],
        "skills": {
            "python": "ADVANCED", "machine-learning": "INTERMEDIATE",
            "pytorch": "BEGINNER", "scikit-learn": "INTERMEDIATE",
            "docker": "BEGINNER", "sql": "INTERMEDIATE", "problem-solving": "ADVANCED",
        },
    },
    {
        "name": "security",
        "target": "cybersecurity-analyst",
        "interests": ["Cybersecurity"],
        "roles": ["Cybersecurity Analyst"],
        "skills": {
            "network-security": "INTERMEDIATE", "owasp": "INTERMEDIATE",
            "linux": "INTERMEDIATE", "python": "BEGINNER",
            "cryptography": "BEGINNER", "critical-thinking": "ADVANCED",
        },
    },
    {
        "name": "devops",
        "target": "devops-engineer",
        "interests": ["DevOps", "Cloud"],
        "roles": ["DevOps Engineer", "Cloud Engineer"],
        "skills": {
            "linux": "ADVANCED", "docker": "INTERMEDIATE", "git": "ADVANCED",
            "ci-cd": "INTERMEDIATE", "shell-scripting": "INTERMEDIATE",
            "aws": "BEGINNER", "ownership": "ADVANCED",
        },
    },
    {
        "name": "fullstack",
        "target": "full-stack-developer",
        "interests": ["Full Stack Development"],
        "roles": ["Full Stack Developer"],
        "skills": {
            "javascript": "ADVANCED", "react": "INTERMEDIATE", "nodejs": "INTERMEDIATE",
            "sql": "INTERMEDIATE", "git": "ADVANCED", "rest-api": "INTERMEDIATE",
            "python": "BEGINNER", "problem-solving": "ADVANCED",
        },
    },
    {
        "name": "design",
        "target": "ui-ux-designer",
        "interests": ["Product Design", "User Research"],
        "roles": ["UI/UX Designer"],
        "skills": {
            "figma": "ADVANCED", "ui-design": "INTERMEDIATE", "ux-research": "INTERMEDIATE",
            "wireframing": "ADVANCED", "communication": "ADVANCED",
            "customer-focus": "ADVANCED",
        },
    },
    {
        "name": "qa",
        "target": "qa-engineer",
        "interests": ["Quality Engineering"],
        "roles": ["QA Engineer"],
        "skills": {
            "manual-testing": "ADVANCED", "test-automation": "INTERMEDIATE",
            "selenium": "BEGINNER", "sql": "INTERMEDIATE", "jira": "INTERMEDIATE",
            "critical-thinking": "ADVANCED",
        },
    },
    {
        "name": "analyst",
        "target": "business-analyst",
        "interests": ["Business Analysis", "Product"],
        "roles": ["Business Analyst", "Product Manager"],
        "skills": {
            "business-analysis": "INTERMEDIATE", "sql": "INTERMEDIATE",
            "excel": "ADVANCED", "requirements-gathering": "INTERMEDIATE",
            "communication": "ADVANCED", "stakeholder-management": "INTERMEDIATE",
        },
    },
]

FIRST_NAMES = [
    "Aditi", "Rohan", "Meera", "Arjun", "Kavya", "Ishaan", "Sneha", "Vikram",
    "Ananya", "Karthik", "Priya", "Rahul", "Divya", "Aryan", "Nisha", "Siddharth",
    "Tara", "Manav", "Pooja", "Aditya", "Ritika", "Harsh", "Lakshmi", "Nikhil",
    "Sanya", "Varun", "Neha", "Kabir", "Shreya", "Dev", "Isha", "Yash",
    "Anjali", "Raghav", "Simran", "Ayaan", "Trisha", "Om", "Bhavna", "Kunal",
    "Rhea", "Sarthak", "Tanvi", "Gaurav", "Mira", "Vivaan", "Aarohi", "Nakul",
    "Sara", "Aman",
]

LAST_NAMES = [
    "Sharma", "Verma", "Iyer", "Nair", "Reddy", "Patel", "Singh", "Gupta",
    "Desai", "Menon", "Joshi", "Kulkarni", "Rao", "Bose", "Chatterjee", "Kapoor",
    "Malhotra", "Pillai", "Banerjee", "Shah", "Mehta", "Agarwal", "Choudhury",
    "Bhat", "Kamath",
]

FACULTY_NAMES = [
    ("Dr. Sunita", "Deshmukh", "Professor", "Computer Engineering"),
    ("Dr. Rajesh", "Krishnan", "Associate Professor", "Artificial Intelligence"),
    ("Dr. Fatima", "Sheikh", "Professor", "Cyber Security"),
    ("Dr. Anand", "Subramanian", "Assistant Professor", "Data Science"),
    ("Dr. Leela", "Nambiar", "Professor", "Software Engineering"),
    ("Dr. Vikas", "Chauhan", "Associate Professor", "Information Technology"),
    ("Dr. Padma", "Raghavan", "Professor", "Computer Science"),
    ("Dr. Imran", "Qureshi", "Assistant Professor", "Electronics Engineering"),
    ("Dr. Shalini", "Prabhu", "Associate Professor", "Product Design"),
    ("Dr. Mohan", "Bhattacharya", "Professor", "Machine Learning"),
]

PROJECT_IDEAS = [
    ("Campus Placement Tracker", "A dashboard that tracks applications and outcomes for a college placement cell.",
     ["Python", "PostgreSQL", "React"]),
    ("Expense Splitter API", "A REST API for splitting shared expenses, with settlement suggestions.",
     ["Python", "FastAPI", "PostgreSQL"]),
    ("Library Seat Availability App", "Real-time seat availability using IoT occupancy sensors.",
     ["Python", "React", "Redis"]),
    ("Resume Keyword Analyser", "Extracts skills from a resume and compares them with a job description.",
     ["Python", "NLP", "Pandas"]),
    ("Crop Yield Predictor", "Predicts yield from weather and soil data for smallholder farms.",
     ["Python", "scikit-learn", "Pandas"]),
    ("Accessible Quiz Platform", "A quiz tool built to WCAG AA, tested with screen readers.",
     ["React", "TypeScript", "Web Accessibility"]),
    ("Network Intrusion Dashboard", "Visualises suspicious traffic patterns from packet captures.",
     ["Python", "Network Security", "Data Visualisation"]),
    ("CI Pipeline Template Library", "Reusable GitHub Actions workflows for student projects.",
     ["CI/CD", "GitHub Actions", "Docker"]),
    ("Local Transit Route Planner", "Shortest-path routing over a city bus network.",
     ["Java", "Algorithms", "SQL"]),
    ("Study Group Matcher", "Matches students into study groups by subject and availability.",
     ["Node.js", "MongoDB", "React"]),
    ("Hospital Queue Simulator", "Simulates outpatient queues to test staffing policies.",
     ["Python", "Statistics", "Data Visualisation"]),
    ("Open Source Contribution Tracker", "Tracks a cohort's open-source contributions over a semester.",
     ["Python", "REST API Design", "PostgreSQL"]),
]

ACHIEVEMENTS = [
    ("Smart India Hackathon", "HACKATHON", "Finalist"),
    ("Inter-college Coding Championship", "COMPETITION", "Winner"),
    ("Department Merit Scholarship", "SCHOLARSHIP", None),
    ("Technical Secretary, Computer Society", "LEADERSHIP", None),
    ("Open Source Contributor, Hacktoberfest", "COMPETITION", "Completed"),
    ("Best Project Award, Final Year Showcase", "COMPETITION", "Winner"),
    ("Volunteer Coordinator, Annual Tech Fest", "VOLUNTEERING", None),
]
