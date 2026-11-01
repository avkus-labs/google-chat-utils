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
        assert r["status"] == "ok"

    def test_partial_coverage_lists_missing(self):
        d = make_distilled("блок (ходы 1–2)\n")
        r = verify(d, SOURCE, 4)
        tc = r["turn_coverage"]
        assert "warning" in tc
        assert "missed" in tc
        assert tc["missed"] == [3, 4]
        # 006.B: missed turns => status=warning
        assert r["status"] == "warning"

    def test_no_anchors_single_warning(self):
        d = make_distilled("текст без ссылок на ходы")
        r = verify(d, SOURCE, 4)
        assert "turn_anchors_missing" in r["turn_coverage"]["warning"]
        assert r["status"] == "warning"

    def test_single_turn_anchor(self):
        d = make_distilled("(ходы 1–3) и отдельно (ход 4)")
        r = verify(d, SOURCE, 4)
        assert r["turn_coverage"] == {"ok": True, "covered": 4}
        assert r["status"] == "ok"

    def test_stub_anchor_same_number(self):
        """006.B: (ходы 5–5) stub anchor should count as anchor_issue."""
        d = make_distilled("(ходы 1–4) и заглушка (ходы 5–5)\n")
        r = verify(d, SOURCE, 4)
        # The stub anchor is out-of-range (5 > 4 turn_count) so is anchor_issue
        assert r.get("anchor_issues", 0) >= 1
        assert r["status"] == "warning"

    def test_anchor_out_of_range(self):
        """006.B: anchor > turn_count => anchor_issue + warning."""
        d = make_distilled("(ходы 1–10)\n")
        r = verify(d, SOURCE, 4)
        assert r.get("anchor_issues", 0) >= 1
        assert r["status"] == "warning"

    def test_full_coverage_is_ok_status(self):
        d = make_distilled("(ходы 1–4)\n")
        r = verify(d, SOURCE, 4)
        assert r["status"] == "ok"
        assert r["turn_coverage"]["ok"] is True


class TestCodeBlocks:
    def test_matching_block_ok(self):
        d = make_distilled("(ходы 1–4)\n```bash\necho hi\n```\n")
        r = verify(d, SOURCE, 4)
        assert r["code_blocks"]["ok"] is True

    def test_whitespace_normalized(self):
        # trailing spaces in distilled → normalized → matches source
        d = make_distilled("(ходы 1–4)\n```bash\necho hi   \n```\n")
        r = verify(d, SOURCE, 4)
        assert r["code_blocks"]["ok"] is True

    def test_hallucinated_block_warning_not_error(self):
        """006.C: code block with invented lines → suspicious, status=warning (not error)."""
        fabricated = "\n".join(f"fake_line_{i}" for i in range(5))
        d = make_distilled(f"(ходы 1–4)\n```\n{fabricated}\n```\n")
        r = verify(d, SOURCE, 4)
        assert "suspicious" in r["code_blocks"]
        assert r["status"] == "warning"

    def test_block_from_source_not_suspicious(self):
        """006.C: block lines all present in source → not suspicious."""
        # Use lines from SOURCE verbatim
        d = make_distilled("(ходы 1–4)\n```bash\necho hi\n```\n")
        r = verify(d, SOURCE, 4)
        assert r["code_blocks"]["ok"] is True
        assert "suspicious" not in r["code_blocks"]

    def test_crlf_normalization_not_false_positive(self):
        """006.C: CRLF in source vs LF in distilled → still matches."""
        crlf_source = SOURCE.replace("\n", "\r\n")
        d = make_distilled("(ходы 1–4)\n```bash\necho hi\n```\n")
        r = verify(d, crlf_source, 4)
        assert r["code_blocks"]["ok"] is True

    def test_ellipsis_normalization(self):
        """006.C: … in distilled normalized to ... → not suspicious if ... present in source."""
        src_with_dots = SOURCE + "\n```\nfoo...bar\n```\n"
        d = make_distilled("(ходы 1–4)\n```\nfoo\u2026bar\n```\n")
        r = verify(d, src_with_dots, 4)
        assert r["code_blocks"]["ok"] is True

    def test_30pct_threshold(self):
        """006.C: exactly 30% fake lines → NOT suspicious; >30% → suspicious."""
        # 3 lines: 1 fake, 2 real → 33% → suspicious
        real_lines = "echo hi\ndone\n"
        src = SOURCE + f"```bash\n{real_lines}```\n"
        # distilled: 2 real + 1 fake
        d_suspicious = make_distilled(
            "(ходы 1–4)\n```bash\necho hi\ndone\nfake_invented_xyz\n```\n"
        )
        r = verify(d_suspicious, src, 4)
        assert "suspicious" in r["code_blocks"]


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

    def test_si_only_skips_turn_coverage(self):
        """007: source_kind=system_instruction => no turn_coverage in result."""
        d = make_distilled("текст без якорей")
        r = verify(d, SOURCE, 0, source_kind="system_instruction")
        assert "turn_coverage" not in r
        assert "length_ratio" not in r
        # status ok if no secrets
        assert r["status"] == "ok"

    def test_si_only_still_checks_secrets(self):
        """007: SI-only verify still catches secrets."""
        d = make_distilled("sk-" + "x" * 30)
        r = verify(d, SOURCE, 0, source_kind="system_instruction")
        assert r["status"] == "error"
        assert "secrets" in r
