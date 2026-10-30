"""Tests for chunker: turn boundaries, code-block safety, numbering."""

from utils.distillation import chunker


SAMPLE = """# Chat: test

### System Instruction
> be nice

### **User**
hello
### **Model**
hi there
### **User**
second question
### **Model**
second answer
"""


class TestSystemInstruction:
    def test_si_replaced_with_placeholder(self):
        out, si = chunker.extract_and_omit_system_instruction(SAMPLE)
        assert "be nice" not in out
        assert "[system instruction omitted:" in out
        assert "sha1" in out
        assert si is not None and "be nice" in si

    def test_no_si(self):
        text = "# Chat\n\n### **User**\nhi\n"
        out, si = chunker.extract_and_omit_system_instruction(text)
        assert out == text
        assert si is None


class TestThoughts:
    def test_thoughts_removed(self):
        text = "a\n<details><summary>🧠 Model Thoughts</summary>\n\nsecret plan\n\n</details>\nb"
        out = chunker.remove_thoughts(text)
        assert "secret plan" not in out
        assert "a" in out and "b" in out


class TestNumbering:
    def test_numbers_assigned(self):
        text = "### **User**\nx\n### **Model**\ny\n### **User**\nz\n"
        out, n = chunker.number_turns(text)
        assert n == 3
        assert "### **User** [#1]" in out
        assert "### **Model** [#2]" in out
        assert "### **User** [#3]" in out


class TestChunking:
    def _numbered(self, body="### **User** [#1]\nq\n### **Model** [#2]\na\n"):
        return "# Chat: t\n\n" + body

    def test_small_text_single_chunk(self):
        chunks = chunker.chunk_markdown(self._numbered(), chunk_tokens=10000)
        assert len(chunks) == 1

    def test_turn_boundary_split(self):
        turn1 = "### **User** [#1]\n" + "x" * 500 + "\n"
        turn2 = "### **Model** [#2]\n" + "y" * 500 + "\n"
        chunks = chunker.chunk_markdown(self._numbered(turn1 + turn2),
                                        chunk_tokens=400)
        assert len(chunks) == 2
        # each chunk keeps the preamble
        assert chunks[0].startswith("# Chat: t")
        assert chunks[1].startswith("# Chat: t")
        # turns not interleaved across chunks
        assert "[#1]" in chunks[0] and "[#2]" not in chunks[0]

    def test_code_block_not_cut(self):
        code = "```python\n" + "\n".join(f"line{i} = {i}" for i in range(50)) + "\n```\n"
        turn = "### **Model** [#1]\nintro\n" + code
        # budget big enough for the turn -> single chunk, code intact
        chunks = chunker.chunk_markdown(self._numbered(turn), chunk_tokens=100000)
        assert len(chunks) == 1
        assert code.rstrip("\n") in chunks[0]

    def test_oversized_code_block_force_split(self):
        code = "```python\n" + "\n".join(f"line{i} = {i}" * 5 for i in range(500)) + "\n```\n"
        turn = "### **Model** [#1]\n" + code
        chunks = chunker.chunk_markdown(self._numbered(turn), chunk_tokens=1000)
        assert len(chunks) > 1
        joined = "\n".join(chunks)
        assert "[... код разбит на части для дистилляции:" in joined

    def test_oversized_turn_paragraph_split_with_continuation(self):
        paras = "\n\n".join("абзац " + "слово " * 100 for _ in range(10))
        turn = "### **User** [#1]\n" + paras + "\n"
        chunks = chunker.chunk_markdown(self._numbered(turn), chunk_tokens=500)
        assert len(chunks) > 1
        assert any("(продолжение)" in c for c in chunks[1:])

    def test_budget_respected(self):
        turn = "### **User** [#1]\n" + "данные " * 2000 + "\n"
        chunks = chunker.chunk_markdown(self._numbered(turn), chunk_tokens=500)
        limit = chunker.char_budget(500) + 300  # small tolerance for marker text
        assert all(len(c) <= limit for c in chunks)

    def test_no_turns_no_chunks(self):
        chunks = chunker.chunk_markdown("just text, no turns", chunk_tokens=100)
        assert chunks == []