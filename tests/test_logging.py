import logging
from utils.logging_config import setup_logging, get_logger, PROJECT_LOGGER_NAME


def test_get_logger_naming():
    logger_root = get_logger()
    assert logger_root.name == PROJECT_LOGGER_NAME

    logger_child = get_logger("parser")
    assert logger_child.name == f"{PROJECT_LOGGER_NAME}.parser"

    # Already prefixed
    logger_prefixed = get_logger(f"{PROJECT_LOGGER_NAME}.custom")
    assert logger_prefixed.name == f"{PROJECT_LOGGER_NAME}.custom"


def test_setup_logging_verbose():
    logger = setup_logging(verbose=True)
    assert logger.level == logging.DEBUG


def test_setup_logging_level_string():
    logger = setup_logging(level="WARNING")
    assert logger.level == logging.WARNING


def test_setup_logging_file_output(tmp_path):
    log_file = tmp_path / "test.log"
    logger = setup_logging(level="INFO", log_file=str(log_file))
    logger.info("Test message for file logging")

    # Flush handlers
    for h in logger.handlers:
        h.flush()

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Test message for file logging" in content
    assert "[INFO]" in content

