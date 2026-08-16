import re


def detect_years_of_experience(resume_data: dict) -> float:
    """Estimate years of professional experience from resume data.

    Sources, in order:
      1. Explicit 'years_of_experience' from AI resume parsing.
      2. Experience entries with a years field (sum of spans).
      3. Grep raw text for 'X+ years' style patterns.
    Returns 0.0 when nothing is found.
    """
    explicit = resume_data.get("years_of_experience")
    if explicit:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:\+)?\s*years?", str(explicit), re.IGNORECASE)
        if match:
            return float(match.group(1))

    experience_entries = resume_data.get("experience", []) or []
    total = 0.0
    for entry in experience_entries:
        if not isinstance(entry, dict):
            continue
        years = entry.get("years") or ""
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:\+)?\s*years?", str(years), re.IGNORECASE)
        if match:
            total += float(match.group(1))
        else:
            # Attempt date-range spans like 2020 - 2023.
            dates = re.findall(r"(19|20)\d{2}", str(entry))
            if len(dates) >= 2:
                total += abs(int(dates[-1]) - int(dates[0]))
    if total:
        return round(total, 1)

    raw = resume_data.get("parsed_text", "") or ""
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:\+)?\s*years?\s+(?:of\s+)?experience", raw, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return 0.0