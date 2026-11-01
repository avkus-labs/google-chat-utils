"""Deterministic (no LLM) verification of a distilled document against its source."""

import re
from typing import Any, Dict, List, Optional, Tuple

from utils.distillation.redactor import _SECRET_PATTERNS

TURN_ANCHOR_RE = re.compile(r"\(ходы?\s+(\d+)(?:[–\-](\d+))?\)")
# Stub anchors: literal (ходы N–N), or [не указаны] / [не указан]
STUB_ANCHOR_RE = re.compile(
    r"\(ходы?\s+(?:[a-zA-Z][–\-][a-zA-Z]|\[не\s+указан[ыо]?\])\)",
    re.IGNORECASE
)
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
    """Normalize text for comparison: CRLF→LF, trailing spaces, typographic chars→ASCII."""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # Typographic → ASCII
    s = s.replace("\u2026", "...")   # … → ...
    s = s.replace("\u2014", "--")   # em-dash → --
    s = s.replace("\u2013", "-")    # en-dash → -
    s = s.replace("\u201c", '"').replace("\u201d", '"')   # "" → ""
    s = s.replace("\u2018", "'").replace("\u2019", "'")   # '' → ''
    # Collapse multiple spaces/tabs to single space
    s = re.sub(r"[ \t]+", " ", s)
    return "\n".join(line.rstrip() for line in s.split("\n")).strip("\n")


def verify(distilled: str, source: str, turn_count: int,
           source_kind: Optional[str] = None) -> Dict[str, Any]:
    """Run all checks; never modifies output files.

    Returns a dict suitable for embedding into the frontmatter
    `verification:` block and printing to console.

    source_kind: if 'system_instruction', skip turn coverage check.
    """
    result: Dict[str, Any] = {"status": "ok"}
    warnings: List[str] = []  # accumulate warning reasons

    # 1. Turn coverage (skip for SI-only documents)
    if source_kind != "system_instruction":
        found: List[Tuple[int, int]] = []
        anchor_issues = 0

        for m in TURN_ANCHOR_RE.finditer(distilled):
            a = int(m.group(1))
            has_range = bool(m.group(2))
            b = int(m.group(2)) if has_range else a
            found.append((a, b))
            # Check degenerate range stub: (ходы 5–5)
            if has_range and a == b:
                anchor_issues += 1
            # Check out-of-range anchors
            elif turn_count > 0 and (a < 1 or b > turn_count):
                anchor_issues += 1

        # Check for literal stubs like (ходы N–N), (ходы [не указаны]), etc.
        for _m in STUB_ANCHOR_RE.finditer(distilled):
            anchor_issues += 1

        if anchor_issues:
            result["anchor_issues"] = anchor_issues
            warnings.append(f"anchor_issues={anchor_issues}")

        if not found:
            result["turn_coverage"] = {
                "warning": "turn_anchors_missing: модель проигнорировала формат ссылок на ходы"
            }
            warnings.append("turn_anchors_missing")
        else:
            covered = set()
            for a, b in found:
                covered.update(range(a, b + 1))
            missing = sorted(set(range(1, turn_count + 1)) - covered)
            if missing:
                result["turn_coverage"] = {
                    "warning": f"пропущено {len(missing)} ходов",
                    "missed": missing,
                }
                warnings.append(f"missed_turns={len(missing)}")
            else:
                result["turn_coverage"] = {"ok": True, "covered": turn_count}

    # 2. Code-block provenance: line-by-line check (006.C)
    #    A block is suspicious if > 30% of its non-empty lines are not found in source
    #    (minimum 2 lines threshold).
    suspicious: List[int] = []
    total_blocks = 0
    norm_source_lines = set(_normalize(source).splitlines())
    for i, m in enumerate(CODE_BLOCK_RE.finditer(distilled), 1):
        block_raw = m.group(1)
        if not block_raw.strip():
            continue
        total_blocks += 1
        block_norm = _normalize(block_raw)
        block_lines = [ln for ln in block_norm.splitlines() if ln.strip()]
        if len(block_lines) < 2:
            # Too short to judge
            continue
        missing_lines = sum(1 for ln in block_lines if ln not in norm_source_lines)
        ratio = missing_lines / len(block_lines)
        if ratio > 0.30:
            suspicious.append(i)

    if suspicious:
        result["code_blocks"] = {
            "warning": f"блоки {suspicious} подозрительны (>30% строк не найдено в источнике)",
            "suspicious": suspicious,
            "total": total_blocks,
        }
        warnings.append(f"suspicious_code_blocks={len(suspicious)}")
    else:
        result["code_blocks"] = {"ok": True, "total": total_blocks}

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

    # 4. Set status = warning if any warnings accumulated (and not already error)
    if warnings and result["status"] != "error":
        result["status"] = "warning"

    # 5. Frontmatter + ratio
    fm_ok, _ = parse_frontmatter(distilled)
    result["frontmatter_valid"] = fm_ok
    if source_kind != "system_instruction":
        result["length_ratio"] = round(len(distilled) / max(len(source), 1), 4)

    return result
