"""Tests for services.notes module."""

from unittest.mock import MagicMock

import pytest

from notebooklm_tools.services.errors import ServiceError, ValidationError
from notebooklm_tools.services.notes import (
    create_note,
    delete_note,
    list_notes,
    update_note,
)


@pytest.fixture
def mock_client():
    return MagicMock()


class TestListNotes:
    """Test list_notes service function."""

    def test_returns_notes_and_count(self, mock_client):
        mock_client.list_notes.return_value = [
            {"id": "note-1", "title": "First", "preview": "Hello..."},
            {"id": "note-2", "title": "Second", "preview": "World..."},
        ]

        result = list_notes(mock_client, "nb-123")

        assert result["notebook_id"] == "nb-123"
        assert result["count"] == 2
        assert len(result["notes"]) == 2

    def test_empty_notebook(self, mock_client):
        mock_client.list_notes.return_value = []

        result = list_notes(mock_client, "nb-123")

        assert result["count"] == 0
        assert result["notes"] == []

    def test_api_error_raises_service_error(self, mock_client):
        mock_client.list_notes.side_effect = RuntimeError("API error")
        with pytest.raises(ServiceError, match="Failed to list notes"):
            list_notes(mock_client, "nb-123")


class TestCreateNote:
    """Test create_note service function."""

    def test_successful_creation(self, mock_client):
        mock_client.create_note.return_value = {"id": "note-new", "title": "My Note"}

        result = create_note(mock_client, "nb-123", "Note content", "My Note")

        assert result["note_id"] == "note-new"
        assert result["title"] == "My Note"
        assert "Note content" in result["content_preview"]

    def test_empty_content_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Content is required"):
            create_note(mock_client, "nb-123", "")

    def test_whitespace_content_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Content is required"):
            create_note(mock_client, "nb-123", "   ")

    def test_long_content_preview_truncated(self, mock_client):
        long_content = "x" * 200
        mock_client.create_note.return_value = {"id": "note-new", "title": "Title"}

        result = create_note(mock_client, "nb-123", long_content)

        assert len(result["content_preview"]) == 103  # 100 chars + "..."
        assert result["content_preview"].endswith("...")

    def test_default_title_used(self, mock_client):
        mock_client.create_note.return_value = {"id": "note-new", "title": "New Note"}

        create_note(mock_client, "nb-123", "content")

        mock_client.create_note.assert_called_once_with("nb-123", "content", "New Note")

    def test_no_id_in_result_raises_service_error(self, mock_client):
        mock_client.create_note.return_value = {}
        with pytest.raises(ServiceError, match="no ID"):
            create_note(mock_client, "nb-123", "content")

    def test_api_error_raises_service_error(self, mock_client):
        mock_client.create_note.side_effect = RuntimeError("fail")
        with pytest.raises(ServiceError, match="Failed to create note"):
            create_note(mock_client, "nb-123", "content")


class TestUpdateNote:
    """Test update_note service function."""

    def test_update_content(self, mock_client):
        mock_client.update_note.return_value = True

        result = update_note(mock_client, "nb-123", "note-1", content="New content")

        assert result["updated"] is True
        assert "content" in result["message"].lower()

    def test_update_title(self, mock_client):
        mock_client.update_note.return_value = True

        result = update_note(mock_client, "nb-123", "note-1", title="New Title")

        assert result["updated"] is True
        assert "New Title" in result["message"]

    def test_update_both(self, mock_client):
        mock_client.update_note.return_value = True

        result = update_note(mock_client, "nb-123", "note-1", content="c", title="t")

        assert result["updated"] is True

    def test_neither_raises_validation_error(self, mock_client):
        with pytest.raises(ValidationError, match="Must provide"):
            update_note(mock_client, "nb-123", "note-1")

    def test_falsy_result_raises_service_error(self, mock_client):
        mock_client.update_note.return_value = None
        with pytest.raises(ServiceError, match="falsy result"):
            update_note(mock_client, "nb-123", "note-1", content="stuff")

    def test_api_error_raises_service_error(self, mock_client):
        mock_client.update_note.side_effect = RuntimeError("fail")
        with pytest.raises(ServiceError, match="Failed to update note"):
            update_note(mock_client, "nb-123", "note-1", content="stuff")


class TestDeleteNote:
    """Test delete_note service function."""

    def test_successful_deletion(self, mock_client):
        mock_client.delete_note.return_value = True

        result = delete_note(mock_client, "nb-123", "note-1")

        assert "note-1" in result["message"]
        assert "deleted" in result["message"].lower()

    def test_falsy_result_raises_service_error(self, mock_client):
        mock_client.delete_note.return_value = None
        with pytest.raises(ServiceError, match="falsy result"):
            delete_note(mock_client, "nb-123", "note-1")

    def test_api_error_raises_service_error(self, mock_client):
        mock_client.delete_note.side_effect = RuntimeError("fail")
        with pytest.raises(ServiceError, match="Failed to delete note"):
            delete_note(mock_client, "nb-123", "note-1")
