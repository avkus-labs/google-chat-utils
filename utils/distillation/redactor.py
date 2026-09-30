"""Secret redaction for text before sending to LLM.

Deterministic regex-based first line of defense. Counts are logged,
never the matched values themselves.
"""

import re
from typing import Dict, Tuple


# Ordered list of (name, compiled_regex) pairs.
# Order matters: more specific patterns first to avoid partial matches.
_SECRET_PATTERNS = [
    # PEM private keys (multi-line)
    ("pem_private_key", re.compile(
        r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+PRIVATE KEY-----"
    )),
    # JWT tokens
    ("jwt", re.compile(
        r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
    )),
    # Anthropic / generic sk- keys
    ("sk_key", re.compile(
        r"sk-[A-Za-z0-9_-]{20,}"
    )),
    # Bearer tokens
    ("bearer", re.compile(
        r"Bearer\s+[A-Za-z0-9_\-.]{20,}"
    )),
    # Linear API keys
    ("linear_key", re.compile(
        r"lin_api_[A-Za-z0-9_-]{20,}"
    )),
    # GitHub tokens (ghp_, ghs_, gho_, ghr_)
    ("github_token", re.compile(
        r"gh[psor]_[A-Za-z0-9]{36,}"
    )),
    # Google API keys
    ("google_api_key", re.compile(
        r"AIza[A-Za-z0-9_-]{35}"
    )),
    # AWS access key IDs
    ("aws_key", re.compile(
        r"AKIA[0-9A-Z]{16}"
    )),
    # Slack tokens
    ("slack_token", re.compile(
        r"xox[baprs]-[0-9A-Za-z_-]{10,}"
    )),
    # URL query params: token=..., apiKey=..., api_key=...
    ("url_param_token", re.compile(
        r"(?i)((?:token|api_key|apikey|api-key|access_token|auth_token)=)[A-Za-z0-9%_\-./+]{20,}"
    )),
    # JSON/YAML key-value: "apiKey": "...", api_key: '...'
    ("kv_secret", re.compile(
        r"""(?i)(["']?(?:api_?key|auth_?token|access_?token|secret_?key|password|passwd)["']?\s*[:=]\s*["'])[A-Za-z0-9%_\-./+]{20,}(["'])"""
    )),
]

REDACTED = "[REDACTED]"


def redact_secrets(text: str) -> Tuple[str, Dict[str, int]]:
    """
    Replace secret patterns in text with [REDACTED].

    Returns:
        (redacted_text, counts_dict) where counts_dict maps
        pattern name -> number of replacements.
        Only counts are returned, never matched values.
    """
    counts: Dict[str, int] = {}
    result = text

    for name, pattern in _SECRET_PATTERNS:
        # For url_param_token and kv_secret, preserve the key name part
        if name == "url_param_token":
            result, n = re.subn(
                pattern,
                lambda m: m.group(1) + REDACTED,
                result
            )
        elif name == "kv_secret":
            result, n = re.subn(
                pattern,
                lambda m: m.group(1) + REDACTED + m.group(2),
                result
            )
        else:
            result, n = re.subn(pattern, REDACTED, result)

        if n > 0:
            counts[name] = n

    return result, counts
