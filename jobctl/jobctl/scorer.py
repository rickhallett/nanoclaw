"""Simple keyword scoring against canonical CV content."""

import re
from pathlib import Path

CV_PATH = Path.home() / "code/nanoclaw/docs/job-applications/thinking-machines-devprod/cv.md"

_cv_content: str | None = None


def _load_cv() -> str:
    global _cv_content
    if _cv_content is None:
        if CV_PATH.exists():
            _cv_content = CV_PATH.read_text().lower()
        else:
            _cv_content = ""
    return _cv_content


def score(title: str, description: str | None) -> float:
    """Compute keyword match score: fraction of job key terms found in CV."""
    cv = _load_cv()
    if not cv:
        return 0.0

    text = title or ""
    if description:
        text += " " + description[:200]

    # Extract terms: words of 3+ chars, lowercased
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    # Filter stopwords
    stopwords = {
        'the', 'and', 'for', 'with', 'you', 'our', 'will', 'this', 'that',
        'are', 'have', 'from', 'your', 'was', 'has', 'its', 'not', 'but',
        'who', 'all', 'can', 'more', 'been', 'their', 'they', 'what',
        'also', 'into', 'any', 'use', 'such', 'each', 'than', 'then',
        'some', 'when', 'would', 'where', 'how', 'which', 'one', 'two',
        'new', 'work', 'join', 'role', 'team', 'help', 'build', 'code',
    }
    terms = [w for w in words if w not in stopwords]

    if not terms:
        return 0.0

    matched = sum(1 for t in terms if t in cv)
    return round(matched / len(terms), 3)
