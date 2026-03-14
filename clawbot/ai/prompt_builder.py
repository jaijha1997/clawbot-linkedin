"""Builds GPT system + user prompts from scraped profile data."""

from typing import Any

from clawbot.ai.message_templates import get_random_template


def build_system_prompt(config) -> str:
    return f"""You are writing a LinkedIn direct message on behalf of a {config.ai_persona}.

Rules:
- Write in first person as the founder
- Be conversational, warm, and specific — never generic
- No emojis, no exclamation spam, no "I hope this message finds you well"
- Reference something specific from the recipient's background to show you read their profile
- Maximum {config.message_max_chars} characters
- Do not be salesy or pushy — this is a genuine human outreach
- End with one clear, low-commitment call to action

Product context:
{config.product_context}
"""


def build_user_prompt(profile: dict[str, Any], config) -> str:
    template = get_random_template()

    experience_summary = ""
    if profile.get("experience"):
        exp = profile["experience"][0]
        experience_summary = f"{exp.get('title', '')} at {exp.get('company', '')} ({exp.get('duration', '')})"

    education_summary = ""
    if profile.get("education"):
        edu = profile["education"][0]
        education_summary = f"{edu.get('degree', '')} from {edu.get('school', '')}"

    skills_summary = ", ".join(profile.get("skills", [])[:5]) or "not listed"

    return f"""Write a personalized LinkedIn message to this person.

--- Recipient Profile ---
Name: {profile.get('full_name', 'there')}
Current Role: {profile.get('current_role', 'N/A')} at {profile.get('current_company', 'N/A')}
Headline: {profile.get('headline', 'N/A')}
Location: {profile.get('location', 'N/A')}
About: {profile.get('about', 'Not provided')[:500]}
Recent Experience: {experience_summary}
Education: {education_summary}
Top Skills: {skills_summary}

--- Message Structure to Follow ---
{template['description']}

--- Product Being Promoted ---
Product: {config.product_name}
Context: {config.product_context}

Write only the message body. Do not include a subject line, greeting prefix, or sign-off.
"""
