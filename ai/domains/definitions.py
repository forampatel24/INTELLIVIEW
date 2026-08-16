"""Predefined interview domains and their categories for IntelliVue."""

# Each domain: (name, category, description, focus_skills)
DOMAINS = [
    # --- Programming ---
    ("Programming", "Programming",
     "General programming concepts: data structures, algorithms, problem solving.",
     ["Algorithms", "Data Structures", "Problem Solving", "OOPS", "Complexity Analysis"]),
    ("C++", "Programming",
     "C++ language: pointers, STL, memory management, templates, OOP in C++.",
     ["C++", "STL", "Pointers", "Memory Management", "Templates", "OOP"]),
    ("Java", "Programming",
     "Java: JVM, collections, multithreading, generics, Spring ecosystem.",
     ["Java", "JVM", "Collections", "Multithreading", "Generics", "Spring"]),
    ("Python", "Programming",
     "Python: syntax, data structures, decorators, generators, typing, packaging.",
     ["Python", "Decorators", "Generators", "Typing", "Pandas", "NumPy"]),
    ("JavaScript", "Programming",
     "JavaScript: ES6+, closures, promises, async/await, event loop.",
     ["JavaScript", "ES6", "Promises", "Async/Await", "Event Loop", "Closures"]),
    ("React", "Programming",
     "React: components, hooks, state management, rendering, performance.",
     ["React", "Hooks", "State Management", "Redux", "Component Lifecycle"]),
    ("Node.js", "Programming",
     "Node.js: event loop, streams, modules, Express, async patterns.",
     ["Node.js", "Express", "Streams", "Event Loop", "REST API"]),

    # --- Computer Science ---
    ("SQL", "Computer Science",
     "SQL: queries, joins, indexing, normalization, transactions.",
     ["SQL", "Joins", "Indexing", "Normalization", "Transactions", "MySQL"]),
    ("DBMS", "Computer Science",
     "Database systems: relational model, ACID, locking, query optimization.",
     ["DBMS", "ACID", "Transactions", "ER Model", "Query Optimization", "NoSQL"]),
    ("Operating Systems", "Computer Science",
     "OS: processes, threads, scheduling, memory management, file systems.",
     ["Operating Systems", "Processes", "Threads", "Scheduling", "Memory Management", "Deadlock"]),
    ("Computer Networks", "Computer Science",
     "Networking: OSI/TCP-IP, protocols, routing, sockets, DNS, HTTP.",
     ["Computer Networks", "TCP/IP", "HTTP", "DNS", "Routing", "Sockets"]),
    ("System Design", "Computer Science",
     "Scalable system design: architecture, load balancing, caching, databases.",
     ["System Design", "Architecture", "Load Balancing", "Caching", "Microservices", "Scaling"]),

    # --- DevOps & Cloud ---
    ("DevOps", "DevOps & Cloud",
     "DevOps: CI/CD, containers, orchestration, infrastructure as code, monitoring.",
     ["DevOps", "CI/CD", "Docker", "Kubernetes", "Terraform", "Jenkins"]),
    ("Cloud", "DevOps & Cloud",
     "Cloud computing: AWS/Azure/GCP services, deployment, serverless, storage.",
     ["Cloud", "AWS", "Azure", "GCP", "Serverless", "Virtualization"]),
    ("Linux", "DevOps & Cloud",
     "Linux: shell scripting, file system, processes, permissions, networking.",
     ["Linux", "Bash", "Shell Scripting", "Permissions", "Processes", "Cron"]),

    # --- AI / ML ---
    ("Machine Learning", "AI / ML",
     "ML: supervised/unsupervised learning, model evaluation, feature engineering.",
     ["Machine Learning", "Regression", "Classification", "Clustering", "Feature Engineering", "Scikit-Learn"]),
    ("Deep Learning", "AI / ML",
     "Deep learning: neural networks, CNNs, RNNs, transformers, training tricks.",
     ["Deep Learning", "Neural Networks", "CNN", "RNN", "Transformers", "Backpropagation"]),
    ("Artificial Intelligence", "AI / ML",
     "AI: search algorithms, knowledge representation, reasoning, intelligent agents.",
     ["Artificial Intelligence", "Search Algorithms", "Knowledge Representation", "Reasoning", "Agents"]),
    ("Data Science", "AI / ML",
     "Data science: statistics, data wrangling, visualization, experimentation.",
     ["Data Science", "Statistics", "Data Analysis", "Data Wrangling", "Visualization", "A/B Testing"]),
    ("Business Intelligence", "AI / ML",
     "BI: dashboards, data warehousing, KPIs, reporting, visualization tools.",
     ["Business Intelligence", "Power BI", "Dashboards", "Data Warehousing", "KPIs", "Reporting"]),
    ("Tableau", "AI / ML",
     "Tableau: dashboards, calculated fields, LOD expressions, data blending.",
     ["Tableau", "Dashboards", "Calculated Fields", "LOD Expressions", "Data Blending"]),

    # --- Cybersecurity ---
    ("Cybersecurity", "Cybersecurity",
     "Security: network security, cryptography, web app security, threat analysis.",
     ["Cybersecurity", "Cryptography", "Network Security", "Penetration Testing", "Threat Analysis"]),

    # --- HR / Behavioral ---
    ("HR", "HR & Behavioral",
     "Human resources: hiring, onboarding, employee relations, performance management.",
     ["HR", "Recruitment", "Onboarding", "Performance Management", "Employee Relations"]),
    ("Behavioral", "HR & Behavioral",
     "Behavioral questions: teamwork, leadership, conflict resolution, STAR answers.",
     ["Behavioral", "Teamwork", "Leadership", "Communication", "Conflict Resolution", "STAR"]),
    ("Managerial", "HR & Behavioral",
     "Management: decision making, delegation, team building, strategy execution.",
     ["Managerial", "Decision Making", "Delegation", "Team Building", "Strategy", "Planning"]),

    # --- Business ---
    ("Finance", "Business",
     "Finance: accounting basics, financial statements, budgeting, valuation.",
     ["Finance", "Accounting", "Financial Statements", "Budgeting", "Valuation"]),
    ("Marketing", "Business",
     "Marketing: branding, digital marketing, campaigns, market research.",
     ["Marketing", "Branding", "Digital Marketing", "Campaigns", "Market Research"]),
    ("Sales", "Business",
     "Sales: pipeline, negotiation, closing, CRM, revenue growth.",
     ["Sales", "Negotiation", "Pipeline", "Closing", "CRM", "Revenue"]),
    ("Business Analytics", "Business",
     "Business analytics: KPIs, metrics, dashboards, data-driven decisions.",
     ["Business Analytics", "KPIs", "Metrics", "Dashboards", "SQL", "Decision Making"]),
    ("Case Study", "Business",
     "Case interviews: structuring problems, frameworks, quantitative reasoning.",
     ["Case Study", "Problem Structuring", "Frameworks", "Quantitative Reasoning", "Communication"]),
    ("Aptitude", "Business",
     "Aptitude: logical reasoning, quantitative ability, verbal reasoning.",
     ["Aptitude", "Logical Reasoning", "Quantitative Ability", "Verbal Reasoning"]),
]

# Convenience category list (for dropdowns / grouping)
CATEGORIES = [
    "Programming",
    "Computer Science",
    "DevOps & Cloud",
    "AI / ML",
    "Cybersecurity",
    "HR & Behavioral",
    "Business",
]


def get_domains() -> list[dict]:
    return [
        {"name": name, "category": category, "description": description, "focus_skills": focus_skills}
        for name, category, description, focus_skills in DOMAINS
    ]