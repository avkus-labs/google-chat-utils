"""Deterministic (no LLM) verification of a distilled document against its source."""

import re
from typing import Any, Dict, List, Tuple

from utils.distillation.redactor import _SECRET_PATTERNS

TURN_ANCHOR_RE = re.compile(r"\(ходы?\s+(\d+)(?:[–\-](\d+))?\)")
CODE_BLOCK_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(text: str) -> Tuple[bool, Dict[str, Any]]:
    """Very small YAML-subset frontmatter check: parseable and a mapping."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return False, {}
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(m.group(1))
        if not isinstance(data, dict):
            return False, {}
        return True, data
    except Exception:
        # Fall back to a minimal key: value scan without PyYAML
        data = {}
        for line in m.group(1).split("\n"):
            if ":" in line and not line.startswith(" ") and not line.startswith("-"):
                k, _, v = line.partition(":")
                data[k.strip()] = v.strip()
        return (len(data) > 0), data


def _normalize(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in s.split("\n")).strip("\n")


def verify(distilled: str, source: str, turn_count: int) -> Dict[str, Any]:
    """Run all checks; never modifies output files.

    Returns a dict suitable for embedding into the frontmatter
    `verification:` block and printing to console.
    """
    result: Dict[str, Any] = {"status": "ok"}

    # 1. Turn coverage
    found: List[Tuple[int, int]] = []
    for m in TURN_ANCHOR_RE.finditer(distilled):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        found.append((a, b))

    if not found:
        result["turn_coverage"] = {
            "warning": "turn_anchors_missing: модель проигнорировала формат ссылок на ходы"
        }
    else:
        covered = set()
        for a, b in found:
            covered.update(range(a, b + 1))
        missing = sorted(set(range(1, turn_count + 1)) - covered)
        if missing:
            result["turn_coverage"] = {
                "warning": f"пропущено {len(missing)} ходов",
                "missing": missing,
            }
        else:
            result["turn_coverage"] = {"ok": True, "covered": turn_count}

    # 2. Code-block provenance: every ```-block in distilled must be found
    #    in the source (line-wise, whitespace-normalized). Otherwise WARNING only.
    suspicious: List[int] = []
    norm_source = _normalize(source)
    for i, m in enumerate(CODE_BLOCK_RE.finditer(distilled), 1):
        block = _normalize(m.group(1))
        if not block:
            continue
        if block not in norm_source:
            suspicious.append(i)
    if suspicious:
        result["code_blocks"] = {
            "warning": f"блоки {suspicious} не найдены дословно в источнике"
        }
    else:
        result["code_blocks"] = {"ok": True}

    # 3. Secrets in distilled -> ERROR (exit code 1 handled by caller)
    secret_hits: Dict[str, int] = {}
    for name, pattern in _SECRET_PATTERNS:
        # finditer: findall would return group tuples for patterns with
        # capture groups (url_param_token, kv_secret), undercounting matches.
        n = sum(1 for _ in pattern.finditer(distilled))
        if n:
            secret_hits[name] = n
    if secret_hits:
        result["status"] = "error"
        result["secrets"] = secret_hits
    else:
        result["secrets"] = {"ok": True}

    # 4. Frontmatter + ratio
    fm_ok, _ = parse_frontmatter(distilled)
    result["frontmatter_valid"] = fm_ok
    result["length_ratio"] = round(len(distilled) / max(len(source), 1), 4)

    return result