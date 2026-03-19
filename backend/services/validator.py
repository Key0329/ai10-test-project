"""Input validation and sanitization — the most critical security layer."""

import re
from typing import Optional

# Allowed GitHub organizations / repo prefixes
# Edit this list to match your company's repos
ALLOWED_REPO_PREFIXES = [
    "https://github.com/",
    # Add your org: "https://github.com/your-org/",
]


def validate_repo_url(url: str) -> str:
    """Validate and sanitize repo URL."""
    url = url.strip()
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS URLs allowed")

    if not re.match(r"^https://[\w.\-]+/[\w.\-]+/[\w.\-]+(?:\.git)?$", url):
        raise ValueError("Invalid repo URL format")

    # Uncomment to enforce org whitelist:
    # if not any(url.startswith(prefix) for prefix in ALLOWED_REPO_PREFIXES):
    #     raise ValueError(f"Repo not in allowed list")

    return url


def validate_jira_ticket(ticket: str) -> str:
    """Validate Jira ticket format."""
    ticket = ticket.strip().upper()
    if not re.match(r"^[A-Z]{1,10}-\d{1,6}$", ticket):
        raise ValueError("Invalid Jira ticket format")
    return ticket


def validate_branch(branch: Optional[str]) -> Optional[str]:
    """Validate branch name."""
    if not branch:
        return None
    branch = branch.strip()
    if not re.match(r"^[a-zA-Z0-9._/\-]+$", branch):
        raise ValueError("Invalid branch name characters")
    if len(branch) > 200:
        raise ValueError("Branch name too long")
    return branch


def validate_extra_prompt(prompt: Optional[str]) -> Optional[str]:
    """Validate extra prompt — no shell metacharacters."""
    if not prompt:
        return None
    prompt = prompt.strip()
    if len(prompt) > 2000:
        raise ValueError("Extra prompt too long (max 2000 chars)")
    # These chars should never appear in a prompt for safety
    dangerous = ["`", "$(",  "$(", "&&", "||", ";", "|", ">", "<", "\\n"]
    for d in dangerous:
        if d in prompt:
            raise ValueError(f"Forbidden character sequence in prompt: {d}")
    return prompt
