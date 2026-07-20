"""Tests for NotesMixin class."""

from unittest.mock import patch

import pytest


def test_notes_mixin_import():
    """Test that NotesMixin can be imported."""
    from notebooklm_tools.core.notes import NotesMixin

    assert NotesMixin is not None


def test_notes_mixin_inherits_base():
    """Test that NotesMixin inherits from BaseClient."""
    from notebooklm_tools.core.base import BaseClient
    from notebooklm_tools.core.notes import NotesMixin

    assert issubclass(NotesMixin, BaseClient)


def test_notes_mixin_has_methods():
    """Test that NotesMixin has all expected methods."""
    from notebooklm_tools.core.notes import NotesMixin

    expected_methods = [
        "create_note",
        "list_notes",
        "update_note",
        "delete_note",
    ]

    for method_name in expected_methods:
        assert hasattr(NotesMixin, method_name), f"Missing method: {method_name}"


def test_create_note_calls_rpc():
    """Test that create_note calls the correct RPC."""
    from notebooklm_tools.core.notes import NotesMixin

    with patch.object(NotesMixin, "_refresh_auth_tokens"):  # noqa: SIM117
        with patch.object(NotesMixin, "_call_rpc") as mock_rpc:
            # Mock create response
            mock_rpc.return_value = [["note_id_123", "Test Note"]]

            mixin = NotesMixin(cookies={"test": "cookie"}, csrf_token="test")

            # Mock update_note to avoid second RPC call
            with patch.object(mixin, "update_note") as mock_update:
                mock_update.return_value = {
                    "id": "note_id_123",
                    "title": "Test Note",
                    "content": "Test content",
                }

                result = mixin.create_note("notebook_123", "Test content", "Test Note")

                # Verify create RPC was called
                assert mock_rpc.called
                assert result is not None
                assert result.get("id") == "note_id_123"


def test_list_notes_filters_mind_maps():
    """Test that list_notes filters out mind maps."""
    from notebooklm_tools.core.notes import NotesMixin

    with patch.object(NotesMixin, "_refresh_auth_tokens"):  # noqa: SIM117
        with patch.object(NotesMixin, "_call_rpc") as mock_rpc:
            # Mock response with both note and mind map
            mock_rpc.return_value = [
                [
                    # Regular note
                    ["note_1", ["note_1", "This is a regular note", {}, None, "Note Title"], 1],
                    # Mind map (has JSON with "children")
                    ["note_2", ["note_2", '{"children": []}', {}, None, "Mind Map"], 1],
                ],
                12345678,
            ]

            mixin = NotesMixin(cookies={"test": "cookie"}, csrf_token="test")
            notes = mixin.list_notes("notebook_123")

            # Should only return the note, not the mind map
            assert len(notes) == 1
            assert notes[0]["id"] == "note_1"
            assert notes[0]["title"] == "Note Title"


def test_update_note_requires_notebook_id():
    """Test that update_note requires notebook_id."""
    from notebooklm_tools.core.notes import NotesMixin

    with patch.object(NotesMixin, "_refresh_auth_tokens"):
        mixin = NotesMixin(cookies={"test": "cookie"}, csrf_token="test")

        with pytest.raises(ValueError, match="notebook_id is required"):
            mixin.update_note("note_123", content="New content")


def test_update_note_requires_content_or_title():
    """Test that update_note requires either content or title."""
    from notebooklm_tools.core.notes import NotesMixin

    with patch.object(NotesMixin, "_refresh_auth_tokens"):
        mixin = NotesMixin(cookies={"test": "cookie"}, csrf_token="test")

        with pytest.raises(ValueError, match="Must provide content or title"):
            mixin.update_note("note_123", notebook_id="notebook_123")


def test_delete_note_returns_bool():
    """Test that delete_note returns boolean."""
    from notebooklm_tools.core.notes import NotesMixin

    with patch.object(NotesMixin, "_refresh_auth_tokens"):  # noqa: SIM117
        with patch.object(NotesMixin, "_call_rpc") as mock_rpc:
            mock_rpc.return_value = None  # API returns null on success

            mixin = NotesMixin(cookies={"test": "cookie"}, csrf_token="test")
            result = mixin.delete_note("note_123", "notebook_123")

            assert isinstance(result, bool)
            assert result is True


def test_client_has_notes_methods():
    """Test that NotebookLMClient has notes methods."""
    from notebooklm_tools.core.client import NotebookLMClient

    expected_methods = [
        "create_note",
        "list_notes",
        "update_note",
        "delete_note",
    ]

    for method_name in expected_methods:
        assert hasattr(NotebookLMClient, method_name), f"Missing method: {method_name}"


def test_rpc_constants_exist():
    """Test that RPC constants are defined."""
    from notebooklm_tools.core.base import BaseClient

    assert hasattr(BaseClient, "RPC_CREATE_NOTE")
    assert hasattr(BaseClient, "RPC_GET_NOTES")
    assert hasattr(BaseClient, "RPC_UPDATE_NOTE")
    assert hasattr(BaseClient, "RPC_DELETE_NOTE")

    # Verify the values match the discovered RPCs
    assert BaseClient.RPC_CREATE_NOTE == "CYK0Xb"
    assert BaseClient.RPC_GET_NOTES == "cFji9"
    assert BaseClient.RPC_UPDATE_NOTE == "cYAfTb"
    assert BaseClient.RPC_DELETE_NOTE == "AH0mwd"
