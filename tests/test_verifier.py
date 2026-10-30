"""Tests for the deterministic verifier."""

from utils.distillation.verifier import verify, parse_frontmatter


SOURCE = """# Chat: test

### **User** [#1]
hello
### **Model** [#2]
```bash
echo hi
```
### **User** [#3]
more
### **Model** [#4]
done
"""


def make_distilled(body: str) -> str:
    return "---\ntype: source\ntitle: t\n---\n\n" + body


class TestTurnCoverage:
    def test_full_coverage(self):
        d = make_distilled("блок (ходы 1–4)\n")
        r = verify(d, SOURCE, 4)
        assert r["turn_coverage"] == {"ok": True, "covered": 4}

    def test_partial_coverage_lists_missing(self):
        d = make_distilled("блок (ходы 1–2)\n")
        r = verify(d, SOURCE, 4)
        assert r["turn_coverage"]["missing"] == [3, 4]

    def test_no_anchors_single_warning(self):
        d = make_distilled("текст без ссылок на ходы")
        r = verify(d, SOURCE, 4)
        assert "turn_anchors_missing" in r["turn_coverage"]["warning"]

    def test_single_turn_anchor(self):
        d = make_distilled("(ходы 1–3) и отдельно (ход 4)")
        r = verify(d, SOURCE, 4)
        assert r["turn_coverage"] == {"ok": True, "covered": 4}


class TestCodeBlocks:
    def test_matching_block_ok(self):
        d = make_distilled("(ходы 1–4)\n```bash\necho hi\n```\n")
        r = verify(d, SOURCE, 4)
        assert r["code_blocks"] == {"ok": True}

    def test_whitespace_normalized(self):
        d = make_distilled("(ходы 1–4)\n```bash\necho hi   \n```\n")
        r = verify(d, SOURCE, 4)
        assert r["code_blocks"] == {"ok": True}

    def test_hallucinated_block_warning_not_error(self):
        d = make_distilled("(ходы 1–4)\n```\nrm -rf /\n```\n")
        r = verify(d, SOURCE, 4)
        assert "warning" in r["code_blocks"]
        assert r["status"] == "ok"  # warning only, not fatal


class TestSecrets:
    def test_secret_in_distilled_is_error(self):
        d = make_distilled("(ходы 1–4)\nключ: sk-" + "x" * 30 + "\n")
        r = verify(d, SOURCE, 4)
        assert r["status"] == "error"
        assert r["secrets"].get("sk_key") == 1

    def test_clean_distilled_ok(self):
        d = make_distilled("(ходы 1–4)\nвсё чисто [REDACTED]")
        r = verify(d, SOURCE, 4)
        assert r["status"] == "ok"
        assert r["secrets"] == {"ok": True}


class TestMisc:
    def test_length_ratio(self):
        d = make_distilled("(ходы 1–4)")
        r = verify(d, SOURCE, 4)
        assert 0 < r["length_ratio"] <= 1.5

    def test_frontmatter_valid_flag(self):
        d = make_distilled("(ходы 1–4)")
        assert verify(d, SOURCE, 4)["frontmatter_valid"] is True
        r = verify("no frontmatter", SOURCE, 4)
        assert r["frontmatter_valid"] is False

    def test_parse_frontmatter_minimal(self):
        ok, data = parse_frontmatter("---\ntype: source\ntitle: X\n---\nbody")
        assert ok is True
        assert data.get("type") == "source"