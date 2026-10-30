"""Tests for safe_stem function."""

from utils.distillation.safe_stem import safe_stem


class TestSafeStem:
    def test_simple_ascii(self):
        assert safe_stem("my_chat") == "my_chat"

    def test_cyrillic_preserved(self):
        assert safe_stem("Настройка Hermes Agent") == "Настройка Hermes Agent"

    def test_hash_replaced(self):
        assert safe_stem("Chat #2") == "Chat _2"

    def test_forbidden_chars_replaced(self):
        assert safe_stem('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"

    def test_percent_replaced(self):
        assert safe_stem("100% done") == "100_ done"

    def test_ampersand_replaced(self):
        assert safe_stem("Tom & Jerry") == "Tom _ Jerry"

    def test_trailing_dots_stripped(self):
        assert safe_stem("file...") == "file"

    def test_trailing_spaces_stripped(self):
        assert safe_stem("file   ") == "file"

    def test_empty_becomes_underscore(self):
        assert safe_stem("") == "_"

    def test_only_forbidden_becomes_underscores(self):
        assert safe_stem("###") == "___"

    def test_control_chars_replaced(self):
        assert safe_stem("a\x00b\x1fc") == "a_b_c"

    def test_internal_spaces_preserved(self):
        assert safe_stem("my chat file") == "my chat file"

    def test_hyphens_underscores_preserved(self):
        assert safe_stem("my-chat_file") == "my-chat_file"

    def test_real_world_example(self):
        """The actual Hermes file name from input_data."""
        result = safe_stem("Настройка Hermes Agent и выбор моделей #2")
        assert result == "Настройка Hermes Agent и выбор моделей _2"
        assert '#' not in result
