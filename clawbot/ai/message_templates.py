"""Base message template structures injected into GPT prompts for variation."""

import random

# Each template is a structural guide passed to GPT, not a literal template.
# GPT uses it as a scaffold while filling in personalized content.
TEMPLATES = [
    {
        "id": "hook_then_value",
        "description": (
            "Open with a specific observation about their background or work. "
            "Then briefly explain why you're reaching out and what value you offer. "
            "End with a soft, non-pushy call to action (e.g., 'would love to hear your thoughts')."
        ),
    },
    {
        "id": "mutual_context",
        "description": (
            "Mention a shared context (industry, challenge, or goal relevant to their role). "
            "Bridge that to what you're working on. "
            "Invite them to a low-commitment next step."
        ),
    },
    {
        "id": "direct_founder_outreach",
        "description": (
            "Be direct about who you are and what you're building. "
            "Explain in one sentence why their profile specifically caught your attention. "
            "Ask a genuine, open-ended question related to their work."
        ),
    },
    {
        "id": "problem_first",
        "description": (
            "Lead with a pain point common in their role or industry. "
            "Show that you understand the problem deeply. "
            "Mention what you're building as a potential solution, without being salesy. "
            "Ask if they've experienced this problem."
        ),
    },
    {
        "id": "curiosity_opener",
        "description": (
            "Open with a genuine compliment or observation about their career trajectory. "
            "Express curiosity about a specific aspect of their work. "
            "Use that as a natural bridge to introduce yourself and what you're building."
        ),
    },
]


def get_random_template() -> dict[str, str]:
    """Return a random template to drive message structure variety."""
    return random.choice(TEMPLATES)
