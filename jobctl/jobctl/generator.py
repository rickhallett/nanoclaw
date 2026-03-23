"""Cover letter generation via Anthropic API."""

import os
from pathlib import Path

CV_PATH = Path.home() / "code/nanoclaw/docs/job-applications/thinking-machines-devprod/cv.md"
CL_TEMPLATE_PATH = Path.home() / "code/nanoclaw/docs/job-applications/thinking-machines-devprod/cover-letter.md"

SYSTEM_PROMPT = (
    "You are a professional cover letter writer. Given a canonical CV and a cover letter "
    "template, write a tailored cover letter for the job. Keep the same voice and structure "
    "as the template. Be specific about the role and company. Return only the cover letter text."
)


def generate_cover_letter(company: str, title: str, description: str | None) -> str:
    """Generate a tailored cover letter for a job listing."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")

    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed")

    cv_content = CV_PATH.read_text() if CV_PATH.exists() else "CV not found."
    cl_template = CL_TEMPLATE_PATH.read_text() if CL_TEMPLATE_PATH.exists() else "Cover letter template not found."

    user_message = f"""Canonical CV:
{cv_content}

Cover Letter Template:
{cl_template}

Job Details:
Company: {company}
Role: {title}
Description: {description or 'No description provided.'}

Please write a tailored cover letter for this job, following the voice and structure of the template."""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text
