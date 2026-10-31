"""End-to-end distillation pipeline shared by `parse --distill` and `distill`.

Single entry point: distill_human_markdown(path, cfg). No LLM calls happen
unless cfg.dry_run is False; dry-run only prints the plan.
"""

import datetime
import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from utils.distillation import chunker
from utils.distillation.chunker import estimate_tokens
from utils.distillation.llm_client import (
    DistillCache, LLMFatalError, ChunkFailedError, cache_key, chat_completion,
)
from utils.distillation.redactor import redact_secrets
from utils.distillation.verifier import verify

CHUNK_PROMPT_NAME = "distiller_chunk_prompt.md"
SYNTHESIS_PROMPT_NAME = "distiller_synthesis_prompt.md"
MAX_CHUNKS_PER_FILE = 15  # hard stop: ask the user beyond this


class DistillError(Exception):
    """Fatal pipeline error (exit code 2 category)."""

    def __init__(self, message: str, exit_code: int = 2):
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class DistillConfig:
    llm_base_url: str = ""
    llm_model: str = ""
    llm_synthesis_model: str = ""
    llm_api_key_env: str = "DISTILL_API_KEY"
    prompt_dir: str = "prompts"
    chunk_tokens: int = 30000
    max_total_input_tokens: int = 400000
    max_chunks: Optional[int] = None       # --distill_max_chunks (trial runs)
    distill_thoughts: str = "drop"          # drop|keep
    dry_run: bool = False
    assume_yes: bool = False
    overwrite: bool = False                 # --distill_overwrite: allow overwriting existing _distilled.md
    output_dir: Optional[str] = None        # None = next to input file
    log: callable = print

    @property
    def synthesis_model(self) -> str:
        return self.llm_synthesis_model or self.llm_model


def synthesis_model(cfg: DistillConfig) -> str:
    """Return synthesis model for cfg: cfg.llm_synthesis_model or cfg.llm_model."""
    return cfg.synthesis_model


@dataclass
class PreparedInput:
    text: str                  # numbered, redacted text (LLM input)
    source_hash: str           # sha256 of the original human.md
    turn_count: int
    redaction_counts: Dict[str, int]
    estimated_input_tokens: int
    chunks: List[str] = field(default_factory=list)


def validate_turn_headers(path: str) -> None:
    """A human.md without ### **User**/### **Model** headers is not distillable."""
    with open(path, "r", encoding="utf-8") as f:
        head = f.read(200_000)
    if "### **User**" not in head and "### **Model**" not in head:
        raise DistillError(
            f"В файле нет заголовков '### **User**' / '### **Model**': {path}",
            exit_code=2,
        )


def prepare(input_path: str, cfg: DistillConfig) -> PreparedInput:
    """Read, strip SI/thoughts, redact secrets, number turns, chunk."""
    with open(input_path, "r", encoding="utf-8") as f:
        raw = f.read()
    source_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    text = raw
    text, _si = chunker.extract_and_omit_system_instruction(text)
    if cfg.distill_thoughts == "drop":
        text = chunker.remove_thoughts(text)

    text, counts = redact_secrets(text)
    text, turn_count = chunker.number_turns(text)

    if turn_count == 0:
        raise DistillError(
            f"После нумерации не найдено ни одного хода: {input_path}", exit_code=2)

    chunks = chunker.chunk_markdown(text, cfg.chunk_tokens)
    est_tokens = sum(estimate_tokens(c) for c in chunks)

    if cfg.max_chunks is not None:
        chunks = chunks[:cfg.max_chunks]

    return PreparedInput(
        text=text,
        source_hash=source_hash,
        turn_count=turn_count,
        redaction_counts=counts,
        estimated_input_tokens=est_tokens,
        chunks=chunks,
    )


def plan_line(input_path: str, prep: PreparedInput) -> str:
    est_out = sum(estimate_tokens(c) for c in prep.chunks) // 5  # rough 20% of input
    return (f"  {os.path.basename(input_path)}: ходов={prep.turn_count}, "
            f"чанков={len(prep.chunks)}, "
            f"~вход={prep.estimated_input_tokens} ток., ~выход={est_out} ток.")


def distill_human_markdown(input_path: str, cfg: DistillConfig) -> Optional[str]:
    """Run the full pipeline for one _human.md.

    Returns the path of the written _distilled.md, or None in dry-run.
    Raises DistillError for fatal problems.
    """
    log = cfg.log
    validate_turn_headers(input_path)

    stem = os.path.basename(input_path)
    if stem.endswith("_human.md"):
        stem = stem[:-len("_human.md")]
    elif stem.endswith(".md"):
        stem = stem[:-3]

    out_dir = cfg.output_dir or os.path.dirname(os.path.abspath(input_path))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{stem}_distilled.md")
    if os.path.exists(out_path) and not getattr(cfg, "overwrite", False):
        raise DistillError(
            f"Файл уже существует, перезапись запрещена (удалите вручную): {out_path}")

    prep = prepare(input_path, cfg)

    if len(prep.chunks) > MAX_CHUNKS_PER_FILE:
        raise DistillError(
            f"Слишком много чанков ({len(prep.chunks)} > {MAX_CHUNKS_PER_FILE}) "
            f"для {os.path.basename(input_path)} — остановлено, нужно решение владельца.")

    if prep.estimated_input_tokens > cfg.max_total_input_tokens:
        raise DistillError(
            f"Оценка входа {prep.estimated_input_tokens} > лимита "
            f"{cfg.max_total_input_tokens} токенов — отказ.")

    log(plan_line(input_path, prep))
    log(f"  модели: чанки={cfg.llm_model}, synthesis={cfg.synthesis_model}")
    if prep.redaction_counts:
        log(f"  редакция секретов: {prep.redaction_counts}")

    if cfg.dry_run:
        log("  [dry-run] вызовы LLM пропущены.")
        return None

    # --- Real run ---
    chunk_tpl = _load_prompt(cfg.prompt_dir, CHUNK_PROMPT_NAME)
    synth_tpl = _load_prompt(cfg.prompt_dir, SYNTHESIS_PROMPT_NAME)
    api_key = os.environ.get(cfg.llm_api_key_env, "")
    cache = DistillCache(os.path.join(out_dir, ".distill_cache"))

    chunk_results: List[str] = []
    for i, chunk_text in enumerate(prep.chunks, 1):
        prompt = (chunk_tpl.replace("{chunk_index}", str(i)).replace(
            "{chunk_total}", str(len(prep.chunks)))
            + f'\n\n<fragment index="{i}" total="{len(prep.chunks)}">\n'
            + chunk_text + "\n</fragment>")
        key = cache_key(chunk_text, chunk_tpl, cfg.llm_model, cfg.llm_base_url)
        cached = cache.get(key)
        if cached is not None:
            log(f"  чанк {i}/{len(prep.chunks)}: из кэша")
            chunk_results.append(cached)
            continue
        log(f"  чанк {i}/{len(prep.chunks)}: вызов LLM...")
        try:
            content = chat_completion(
                cfg.llm_base_url, cfg.llm_model, prompt, api_key)
        except ChunkFailedError as e:
            raise DistillError(f"Чанк {i} провален ({e}), частичный результат не пишется.")
        except LLMFatalError as e:
            raise DistillError(f"Ошибка LLM на чанке {i}: {e}", exit_code=1)
        cache.put(key, content)
        chunk_results.append(content)

    merged = "\n\n".join(chunk_results)
    synth_prompt = synth_tpl + "\n\n<distilled_text>\n" + merged + "\n</distilled_text>"
    synth_key = cache_key(merged, synth_tpl, cfg.synthesis_model, cfg.llm_base_url)
    meta_json = cache.get(synth_key)
    if meta_json is None:
        log("  synthesis: вызов LLM...")
        try:
            meta_json = chat_completion(
                cfg.llm_base_url, cfg.synthesis_model, synth_prompt, api_key)
        except LLMFatalError as e:
            raise DistillError(f"Ошибка LLM на synthesis: {e}", exit_code=1)
        cache.put(synth_key, meta_json)

    meta = _parse_json_with_retry(meta_json, cfg)
    body = merged  # chunk outputs are the body; synthesis gives metadata

    verification = verify(
        _frontmatter_only(meta, input_path, prep, cfg) + "\n" + body,
        prep.text, prep.turn_count)

    final = render_distilled(meta, body, verification, input_path, prep, cfg)
    # Atomic write: write to tmp, then replace (old file stays intact on error)
    tmp_path = out_path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(final)
        os.replace(tmp_path, out_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    log(f"  💾 Записан: {out_path}")

    # Re-verify the actually written document
    verification = verify(final, prep.text, prep.turn_count)
    _print_verification(verification, log)
    if verification["status"] == "error":
        raise DistillError(
            "Верификатор нашёл секреты в _distilled.md (файл записан, см. отчёт).",
            exit_code=1)
    return out_path


def _parse_json_with_retry(raw: str, cfg: DistillConfig) -> Dict:
    """Parse synthesis JSON; on failure retry the call once, then error."""
    def attempt(s: str) -> Optional[Dict]:
        s = s.strip()
        if s.startswith("```"):
            s = s.strip("`")
            if s.startswith("json"):
                s = s[4:]
        try:
            data = json.loads(s)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

    data = attempt(raw)
    if data is not None:
        return data

    # one retry
    api_key = os.environ.get(cfg.llm_api_key_env, "")
    retry_prompt = (
        "Предыдущий ответ не был валидным JSON. Верни ТОЛЬКО один валидный "
        "JSON-объект без пояснений.\nИсходный ответ:\n" + raw)
    try:
        retried = chat_completion(
            cfg.llm_base_url, cfg.synthesis_model, retry_prompt, api_key)
    except (LLMFatalError, ChunkFailedError) as e:
        raise DistillError(f"Synthesis: повторный вызов не удался: {e}", exit_code=1)
    data = attempt(retried)
    if data is None:
        raise DistillError("Synthesis вернул невалидный JSON после повтора.", exit_code=1)
    return data


def _load_prompt(prompt_dir: str, name: str) -> str:
    path = os.path.join(prompt_dir, name)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _utc_now() -> str:
    """Full ISO 8601 with explicit UTC offset (OKF v0.2 rejects bare dates)."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _frontmatter_only(meta, input_path, prep, cfg) -> str:
    """Frontmatter string (used for early verification of the header)."""
    now = _utc_now()
    fm = {
        "type": "source",
        "title": meta.get("title", os.path.basename(input_path)),
        "status": "active",
        "trust_tier": "ai-generated",
        "generated": {"by": cfg.llm_model, "at": now},
        "original_source": os.path.basename(input_path),
        "source_sha256": prep.source_hash,
        "chunks": len(prep.chunks),
    }
    if cfg.synthesis_model != cfg.llm_model:
        fm["synthesis_model"] = cfg.synthesis_model
    return _to_yaml(fm)


def _to_yaml(obj, indent: int = 0) -> str:
    pad = "  " * indent
    lines = []
    for k, v in obj.items():
        if isinstance(v, dict):
            lines.append(f"{pad}{k}:")
            lines.append(_to_yaml(v, indent + 1))
        elif isinstance(v, list):
            lines.append(f"{pad}{k}:")
            for item in v:
                lines.append(f"{pad}  - {json.dumps(str(item), ensure_ascii=False)}")
        else:
            lines.append(f"{pad}{k}: {json.dumps(v, ensure_ascii=False)}")
    return "\n".join(lines)


def render_distilled(meta, body, verification, input_path, prep, cfg) -> str:
    now = _utc_now()
    fm_lines = [
        "---",
        "type: source",
        f"title: {json.dumps(meta.get('title', ''), ensure_ascii=False)}",
        "status: active",
        "trust_tier: ai-generated",
        "generated:",
        f"  by: {json.dumps(cfg.llm_model, ensure_ascii=False)}",
        f"  at: {json.dumps(now)}",
    ]
    if cfg.synthesis_model != cfg.llm_model:
        fm_lines.append(f"synthesis_model: {json.dumps(cfg.synthesis_model, ensure_ascii=False)}")
    fm_lines.extend([
        f"original_source: {json.dumps(os.path.basename(input_path), ensure_ascii=False)}",
        f"source_sha256: {prep.source_hash}",
        f"chunks: {len(prep.chunks)}",
        f"description: {json.dumps(meta.get('summary', ''), ensure_ascii=False)}",
        f"resolution: {json.dumps(meta.get('resolution', ''), ensure_ascii=False)}",
        "keywords:",
    ])
    for k in meta.get("keywords", []):
        fm_lines.append(f"  - {json.dumps(str(k), ensure_ascii=False)}")
    fm_lines.append("tags:")
    for t in meta.get("tags", []):
        fm_lines.append(f"  - {json.dumps(str(t), ensure_ascii=False)}")
    fm_lines.append("verification:")
    fm_lines.append(f"  status: {json.dumps(verification.get('status'), ensure_ascii=False)}")
    fm_lines.append(f"  length_ratio: {verification.get('length_ratio')}")
    fm_lines.append("---")

    sections = ["", "# " + str(meta.get("title", "Distilled")), "",
                meta.get("summary", ""), "",
                body, "",
                "## Ключевая информация", ""]
    sections += _kv_section("Решения", meta.get("decisions_made", []))
    sections += _kv_section("Неудачные подходы", meta.get("failed_approaches", []))
    sections += _kv_section("Сигнатуры ошибок", meta.get("error_signatures", []))
    sections += _kv_section("Уроки", meta.get("lessons_learned", []))
    sections += _kv_section("Темы", meta.get("topics_covered", []))
    sections += _kv_section("Открытые вопросы", meta.get("open_questions", []))

    return "\n".join(fm_lines) + "\n" + "\n".join(sections) + "\n"


def _kv_section(title: str, items) -> List[str]:
    if not items:
        return []
    out = [f"### {title}", ""]
    for item in items:
        out.append(f"- {item}")
    out.append("")
    return out


def _print_verification(v: Dict, log) -> None:
    log("  Верификация:")
    for key, val in v.items():
        if key in ("status", "length_ratio"):
            continue
        if isinstance(val, dict):
            if "ok" in val:
                log(f"    {key}: OK")
            elif "warning" in val:
                log(f"    {key}: ⚠️ {val['warning']}")
            else:
                log(f"    {key}: 🔴 {val}")
    log(f"    length_ratio: {v.get('length_ratio')}, status: {v.get('status')}")