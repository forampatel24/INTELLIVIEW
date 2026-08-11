import json
import re

import spacy

COMMON_SKILLS = [
    "python", "java", "javascript", "typescript", "c++", "c", "c#", "go", "rust", "sql", "html", "css",
    "react", "angular", "vue", "node.js", "node", "express", "django", "flask", "fastapi", "spring",
    "spring boot", "flutter", "kotlin", "swift", "php", "ruby", "scala", "perl",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy", "matplotlib", "seaborn",
    "opencv", "mediapipe", "deep learning", "machine learning", "artificial intelligence", "nlp",
    "computer vision", "data science", "data analysis", "statistics", "power bi", "tableau",
    "hadoop", "spark", "kafka", "airflow",
    "mysql", "postgresql", "mongodb", "sqlite", "oracle", "redis", "elasticsearch",
    "docker", "kubernetes", "aws", "azure", "gcp", "terraform", "ansible", "jenkins", "git", "github",
    "linux", "bash", "shell", "networking", "tcp/ip", "http", "rest api", "graphql",
    "agile", "scrum", "jira", "selenium", "pytest", "junit", "testing", "tdd",
    "oops", "data structures", "algorithms", "dbms", "operating systems", "system design",
    "figma", "excel", "powerpoint", "word",
]

SKILL_ALIASES = {
    "node": "Node.js",
    "express": "Express.js",
    "react": "React",
    "nodejs": "Node.js",
    "numpy": "NumPy",
    "pandas": "Pandas",
    "sklearn": "Scikit-Learn",
    "tf": "TensorFlow",
    "dl": "Deep Learning",
    "ml": "Machine Learning",
    "ai": "Artificial Intelligence",
    "dl": "Deep Learning",
}


class SkillExtractor:
    def __init__(self, model_name: str = "en_core_web_sm"):
        self.nlp = spacy.load(model_name, disable=["ner", "parser"])
        self.enabled_pipes = self.nlp.pipe_names

    def extract(self, text: str) -> list[str]:
        found: list[str] = []
        lower = text.lower()
        for skill in COMMON_SKILLS:
            if re.search(rf"(?<![a-z0-9]){re.escape(skill)}(?![a-z0-9])", lower):
                found.append(SKILL_ALIASES.get(skill, skill.title()))
        return list(dict.fromkeys(found))

    def extract_from_sections(self, sections: dict[str, str]) -> list[str]:
        combined = " ".join(v for k, v in sections.items() if k in ("skills", "technologies", "summary"))
        return self.extract(combined)
