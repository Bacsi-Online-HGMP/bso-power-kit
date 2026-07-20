"""Tests for SharingMixin class."""

from unittest.mock import patch

import pytest


def test_sharing_mixin_import():
    """Test that SharingMixin can be imported."""
    from notebooklm_tools.core.sharing import SharingMixin

    assert SharingMixin is not None


def test_sharing_mixin_inherits_base():
    """Test that SharingMixin inherits from BaseClient."""
    from notebooklm_tools.core.base import BaseClient
    from notebooklm_tools.core.sharing import SharingMixin

    assert issubclass(SharingMixin, BaseClient)


def test_sharing_mixin_has_methods():
    """Test that SharingMixin has all expected methods."""
    from notebooklm_tools.core.sharing import SharingMixin

    expected_methods = [
        "get_share_status",
        "set_public_access",
        "add_collaborator",
        "add_collaborators_bulk",
    ]

    for method_name in expected_methods:
        assert hasattr(SharingMixin, method_name), f"Missing method: {method_name}"


def test_get_share_status_uses_correct_rpc():
    """Test that get_share_status calls the correct RPC."""
    from notebooklm_tools.core.sharing import SharingMixin

    with patch.object(SharingMixin, "_refresh_auth_tokens"):  # noqa: SIM117
        with patch.object(SharingMixin, "_call_rpc") as mock_rpc:
            mock_rpc.return_value = []

            mixin = SharingMixin(cookies={"test": "cookie"}, csrf_token="test")
            mixin.get_share_status("notebook_id_123")

            mock_rpc.assert_called_once()
            call_args = mock_rpc.call_args
            assert call_args[0][0] == "JFMDGd"  # RPC_GET_SHARE_STATUS


def test_set_public_access_uses_correct_rpc():
    """Test that set_public_access calls the correct RPC."""
    from notebooklm_tools.core.sharing import SharingMixin

    with patch.object(SharingMixin, "_refresh_auth_tokens"):  # noqa: SIM117
        with patch.object(SharingMixin, "_call_rpc") as mock_rpc:
            mock_rpc.return_value = {}

            mixin = SharingMixin(cookies={"test": "cookie"}, csrf_token="test")
            result = mixin.set_public_access("notebook_id_123", is_public=True)

            mock_rpc.assert_called_once()
            call_args = mock_rpc.call_args
            assert call_args[0][0] == "QDyure"  # RPC_SHARE_NOTEBOOK
            assert result == "https://notebooklm.google.com/notebook/notebook_id_123"


def test_add_collaborator_uses_correct_rpc():
    """Test that add_collaborator calls the correct RPC."""
    from notebooklm_tools.core.sharing import SharingMixin

    with patch.object(SharingMixin, "_refresh_auth_tokens"):  # noqa: SIM117
        with patch.object(SharingMixin, "_call_rpc") as mock_rpc:
            mock_rpc.return_value = {}

            mixin = SharingMixin(cookies={"test": "cookie"}, csrf_token="test")
            result = mixin.add_collaborator("notebook_id_123", "test@example.com", role="editor")

            mock_rpc.assert_called_once()
            call_args = mock_rpc.call_args
            assert call_args[0][0] == "QDyure"  # RPC_SHARE_NOTEBOOK
            assert result is True


def test_add_collaborators_bulk_uses_correct_rpc():
    """Test that add_collaborators_bulk calls the correct RPC with multi-email payload."""
    from notebooklm_tools.core.sharing import SharingMixin

    with patch.object(SharingMixin, "_refresh_auth_tokens"):  # noqa: SIM117
        with patch.object(SharingMixin, "_call_rpc") as mock_rpc:
            mock_rpc.return_value = []

            mixin = SharingMixin(cookies={"test": "cookie"}, csrf_token="test")
            recipients = [
                {"email": "alice@example.com", "role": "viewer"},
                {"email": "bob@example.com", "role": "editor"},
            ]
            result = mixin.add_collaborators_bulk("notebook_id_123", recipients)

            mock_rpc.assert_called_once()
            call_args = mock_rpc.call_args
            assert call_args[0][0] == "QDyure"  # RPC_SHARE_NOTEBOOK

            # Verify the multi-email array structure
            params = call_args[0][1]
            email_items = params[0][0][1]  # [[email, None, role_code], ...]
            assert len(email_items) == 2
            assert email_items[0][0] == "alice@example.com"
            assert email_items[0][2] == 3  # SHARE_ROLE_VIEWER
            assert email_items[1][0] == "bob@example.com"
            assert email_items[1][2] == 2  # SHARE_ROLE_EDITOR
            assert result is True


def test_add_collaborators_bulk_empty_recipients():
    """Test that add_collaborators_bulk raises ValueError for empty list."""
    from notebooklm_tools.core.sharing import SharingMixin

    with patch.object(SharingMixin, "_refresh_auth_tokens"):
        mixin = SharingMixin(cookies={"test": "cookie"}, csrf_token="test")
        with pytest.raises(ValueError, match="Recipients list cannot be empty"):
            mixin.add_collaborators_bulk("notebook_id_123", [])


def test_add_collaborators_bulk_rejects_owner_role():
    """Test that add_collaborators_bulk raises ValueError for owner role."""
    from notebooklm_tools.core.sharing import SharingMixin

    with patch.object(SharingMixin, "_refresh_auth_tokens"):
        mixin = SharingMixin(cookies={"test": "cookie"}, csrf_token="test")
        with pytest.raises(ValueError, match="Cannot add collaborator"):
            mixin.add_collaborators_bulk("notebook_id_123", [{"email": "a@b.com", "role": "owner"}])
