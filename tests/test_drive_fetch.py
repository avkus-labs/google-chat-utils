"""
Unit tests for Google Drive Chat Fetcher using mocks.
"""

import pytest
from unittest.mock import MagicMock, patch
from utils.drive.client import GoogleDriveChatFetcher


@patch("utils.drive.client.get_drive_credentials")
@patch("utils.drive.client.build")
def test_search_chat_files_success(mock_build, mock_get_creds):
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_files = mock_service.files.return_value
    mock_list = mock_files.list.return_value
    mock_list.execute.return_value = {
        "files": [{"id": "123", "name": "Test Chat", "modifiedTime": "2026-09-30T12:00:00Z"}]
    }

    fetcher = GoogleDriveChatFetcher()
    results = fetcher.search_chat_files("Test Chat", folder_id="folder_456")

    assert len(results) == 1
    assert results[0]["id"] == "123"


@patch("utils.drive.client.get_drive_credentials")
@patch("utils.drive.client.build")
def test_fetch_multiple_candidates_raises_error(mock_build, mock_get_creds):
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_files = mock_service.files.return_value
    mock_list = mock_files.list.return_value
    mock_list.execute.return_value = {
        "files": [
            {"id": "123", "name": "Test Chat 1"},
            {"id": "456", "name": "Test Chat 2"}
        ]
    }

    fetcher = GoogleDriveChatFetcher()
    with pytest.raises(RuntimeError, match="Multiple files matching"):
        fetcher.fetch_chat_file("Test Chat", folder_id="folder_456")
