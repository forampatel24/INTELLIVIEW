import re

SECTION_PATTERNS = {
    "summary": [
        r"(?i)^summary$",
        r"(?i)^profile$",
        r"(?i)^objective$",
        r"(?i)^about me$",
        r"(?i)^career objective$",
    ],
    "experience": [
        r"(?i)^experience$",
        r"(?i)^work experience$",
        r"(?i)^professional experience$",
        r"(?i)^employment history$",
        r"(?i)^work history$",
    ],
    "education": [
        r"(?i)^education$",
        r"(?i)^academic background$",
        r"(?i)^academics$",
    ],
    "projects": [
        r"(?i)^projects$",
        r"(?i)^project work$",
        r"(?i)^academic projects$",
        r"(?i)^personal projects$",
    ],
    "skills": [
        r"(?i)^skills$",
        r"(?i)^technical skills$",
        r"(?i)^core competencies$",
        r"(?i)^skill set$",
        r"(?i)^competencies$",
    ],
    "certifications": [
        r"(?i)^certifications$",
        r"(?i)^certificates$",
        r"(?i)^courses$",
        r"(?i)^training$",
    ],
    "technologies": [
        r"(?i)^technologies$",
        r"(?i)^technical stack$",
        r"(?i)^tech stack$",
        r"(?i)^languages and tools$",
        r"(?i)^programming languages$",
    ],
    "achievements": [
        r"(?i)^achievements$",
        r"(?i)^awards$",
        r"(?i)^honors$",
        r"(?i)^extracurricular$",
    ],
    "languages": [
        r"(?i)^languages$",
    ],
    "interests": [
        r"(?i)^interests$",
        r"(?i)^hobbies$",
    ],
    "references": [
        r"(?i)^references$",
        r"(?i)^declaration$",
    ],
}

ALL_PATTERNS = [(section, re.compile(p)) for section, pats in SECTION_PATTERNS.items() for p in pats]


def detect_sections(text: str) -> dict[str, str]:
    """Returns {section_name: section_text} for detected sections."""
    lines = text.splitlines()
    sections: dict[str, str] = {}
    current_section: str | None = None
    current_lines: list[str] = []

    def flush():
        nonlocal current_lines
        if current_section is not None and current_lines:
            content = "\n".join(current_lines).strip()
            if content:
                sections[current_section] = content
        current_lines = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush()
            continue
        detected = None
        for section, pattern in ALL_PATTERNS:
            if pattern.fullmatch(line):
                detected = section
                break
        if detected:
            flush()
            current_section = detected
        elif current_section is not None:
            current_lines.append(raw_line)

    flush()
    return sections


def detect_contact_info(text: str) -> dict[str, str]:
    """Extracts email, phone and links from raw resume text."""
    info: dict[str, str] = {}
    email = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    if email:
        info["email"] = email.group(0)
    phone = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    if phone:
        info["phone"] = phone.group(0)
    linkedin = re.search(r"linkedin\.com/in/[a-zA-Z0-9._-]+", text, re.IGNORECASE)
    if linkedin:
        info["linkedin"] = linkedin.group(0)
    github = re.search(r"github\.com/[a-zA-Z0-9._-]+", text, re.IGNORECASE)
    if github:
        info["github"] = github.group(0)
    return info
