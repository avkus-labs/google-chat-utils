"""Chunking of human.md into LLM-sized pieces.

Token counts are estimated as chars / 2.0 with a 20% safety buffer
(no external tokenizer dependency — deliberately, per task 001 decision).
"""

import hashlib
import re
from typing import List, Optional, Tuple

TOKEN_EST_DIVISOR = 2.0
SAFETY_FACTOR = 0.8  # target only 80% of chunk_tokens

TURN_HEADER_RE = re.compile(r"^### \*\*(User|Model)\*\*\s*$", re.MULTILINE)
NUMBERED_HEADER_RE = re.compile(r"^### \*\*(User|Model)\*\* \[#\d+\]\s*$", re.MULTILINE)
THOUGHTS_RE = re.compile(
    r"<details><summary>🧠 Model Thoughts</summary>[\s\S]*?</details>"
)
SI_SECTION_RE = re.compile(
    r"^### System Instruction\n[\s\S]*?(?=^### |\Z)", re.MULTILINE
)

CONTINUATION_MARK = "(продолжение)"
CODE_SPLIT_MARKER = "[... код разбит на части для дистилляции: часть {k}/{n} ...]"


def estimate_tokens(text: str) -> int:
    """Rough token estimate: chars / 2.0 (covers Cyrillic-heavy text)."""
    return int(len(text) / TOKEN_EST_DIVISOR)


def char_budget(chunk_tokens: int) -> int:
    """Max characters per chunk given the token estimate and safety buffer."""
    return int(chunk_tokens * SAFETY_FACTOR * TOKEN_EST_DIVISOR)


def extract_and_omit_system_instruction(text: str) -> Tuple[str, Optional[str]]:
    """Replace the System Instruction section with a short placeholder."""
    m = SI_SECTION_RE.search(text)
    if not m:
        return text, None
    si = m.group(0)
    sha1 = hashlib.sha1(si.encode("utf-8")).hexdigest()[:12]
    placeholder = f"[system instruction omitted: {len(si)} chars, sha1 {sha1}]\n"
    return text[:m.start()] + placeholder + text[m.end():], si


def remove_thoughts(text: str) -> str:
    """Drop all <details> Model Thoughts blocks."""
    return THOUGHTS_RE.sub("", text)


def number_turns(text: str) -> Tuple[str, int]:
    """Add [#N] anchors to turn headers. Returns (text, turn_count)."""
    counter = 0

    def repl(m):
        nonlocal counter
        counter += 1
        return f"### **{m.group(1)}** [#{counter}]"

    return TURN_HEADER_RE.sub(repl, text), counter


def split_into_turns(text: str) -> Tuple[str, List[str]]:
    """Split numbered text into (preamble, [turn_strings]).

    Each turn string starts with its '### **Role** [#N]' header.
    """
    positions = [m.start() for m in NUMBERED_HEADER_RE.finditer(text)]
    if not positions:
        return text, []
    preamble = text[:positions[0]]
    turns = []
    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        turns.append(text[start:end])
    return preamble, turns


def chunk_markdown(text: str, chunk_tokens: int) -> List[str]:
    """Chunk numbered markdown on turn boundaries.

    Never cuts inside a ```-block unless a single block exceeds the
    budget, in which case it is force-split with explicit markers.
    The preamble (title + SI placeholder) is prepended to every chunk.
    """
    budget = char_budget(chunk_tokens)
    preamble, turns = split_into_turns(text)
    chunks: List[str] = []
    current_parts: List[str] = []
    current_len = len(preamble)

    def flush():
        nonlocal current_parts, current_len
        if current_parts:
            chunks.append(preamble + "".join(current_parts))
            current_parts = []
            current_len = len(preamble)

    for turn in turns:
        if len(turn) > budget:
            flush()
            for seg in split_oversized_turn(turn, budget - len(preamble)):
                chunks.append(preamble + seg)
            continue
        if current_parts and current_len + len(turn) > budget:
            flush()
        current_parts.append(turn)
        current_len += len(turn)
    flush()
    return chunks


def split_oversized_turn(turn: str, budget: int) -> List[str]:
    """Split one oversized turn on paragraph boundaries outside code."""
    segments = _segment_by_fences(turn)
    pieces: List[str] = []
    for kind, seg in segments:
        if len(seg) <= budget:
            pieces.append(seg)
        elif kind == "code":
            pieces.extend(_split_code_block(seg, budget))
        else:
            pieces.extend(_split_text(seg, budget))

    packed: List[str] = []
    cur = ""
    for p in pieces:
        if cur and len(cur) + len(p) + 1 > budget:
            packed.append(cur)
            cur = p
        else:
            cur = cur + "\n" + p if cur else p
    if cur:
        packed.append(cur)

    if len(packed) > 1:
        packed = [packed[0]] + [CONTINUATION_MARK + "\n" + p for p in packed[1:]]
    return packed


def _segment_by_fences(text: str) -> List[Tuple[str, str]]:
    """Split text into ('text', s) / ('code', s) segments.

    Code segments include their opening and closing fences.
    """
    segments: List[Tuple[str, str]] = []
    lines = text.split("\n")
    current: List[str] = []
    in_code = False
    for line in lines:
        stripped = line.lstrip()
        if not in_code and stripped.startswith("```"):
            if current:
                segments.append(("text", "\n".join(current)))
            current = [line]
            in_code = True
        elif in_code and stripped.startswith("```"):
            current.append(line)
            segments.append(("code", "\n".join(current)))
            current = []
            in_code = False
        else:
            current.append(line)
    if current:
        segments.append(("code" if in_code else "text", "\n".join(current)))
    return [(k, v) for k, v in segments if v]


def _split_text(text: str, budget: int) -> List[str]:
    """Split plain text on paragraph, then line boundaries."""
    out: List[str] = []
    cur = ""
    for para in re.split(r"\n{2,}", text):
        candidate = para if not cur else cur + "\n\n" + para
        if len(candidate) <= budget:
            cur = candidate
            continue
        if cur:
            out.append(cur)
            cur = ""
        if len(para) > budget:
            for line in para.split("\n"):
                cand = line if not cur else cur + "\n" + line
                if len(cand) <= budget:
                    cur = cand
                else:
                    if cur:
                        out.append(cur)
                    cur = line[:budget]  # last-resort hard cut
        else:
            cur = para
    if cur:
        out.append(cur)
    return out


def _split_code_block(block: str, budget: int) -> List[str]:
    """Force-split an oversized fenced code block.

    Closes and reopens the fence between parts and adds a language-neutral
    marker so the split is visible to the model.
    """
    lines = block.split("\n")
    open_fence = lines[0]
    body_lines = lines[1:]
    if body_lines and body_lines[-1].lstrip().startswith("```"):
        body_lines = body_lines[:-1]
    per_piece = max(budget - len(open_fence) - 100, 200)

    pieces: List[str] = []
    cur: List[str] = []
    cur_len = 0
    for line in body_lines:
        if cur and cur_len + len(line) + 1 > per_piece:
            pieces.append("\n".join(cur))
            cur, cur_len = [], 0
        cur.append(line)
        cur_len += len(line) + 1
    if cur:
        pieces.append("\n".join(cur))

    n = len(pieces)
    out: List[str] = []
    for k, body in enumerate(pieces, 1):
        block_str = f"{open_fence}\n{body}\n```"
        if k > 1:
            block_str = CODE_SPLIT_MARKER.format(k=k, n=n) + "\n" + block_str
        out.append(block_str)
    return out