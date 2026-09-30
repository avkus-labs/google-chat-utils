"""Safe filename stem generation for output subfolders."""

import re


# Characters forbidden on Windows/NTFS + URL-unsafe characters
_FORBIDDEN_RE = re.compile(r'[<>:"/\\|?*#%&\x00-\x1f]')


def safe_stem(name: str) -> str:
    """
    Convert an arbitrary filename stem into a filesystem-safe directory name.

    Rules:
    - Replace forbidden characters (<>:"/\\|?*#%& and control chars) with '_'.
    - Strip trailing dots and spaces (Windows restriction).
    - Preserve Cyrillic, spaces (internal), hyphens, underscores.
    - If result is empty after sanitization, return '_'.
    """
    result = _FORBIDDEN_RE.sub('_', name)
    # Strip trailing dots and spaces (Windows doesn't allow them)
    result = result.rstrip('. ')
    if not result:
        return '_'
    return result
