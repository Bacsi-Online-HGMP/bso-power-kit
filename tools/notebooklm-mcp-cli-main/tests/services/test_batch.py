"""Tests for batch service — batch operations across notebooks."""

from unittest.mock import MagicMock, patch

import pytest

from notebooklm_tools.services.batch import (
    batch_add_source,
    batch_create,
    batch_delete,
    batch_query,
    batch_studio,
)
from notebooklm_tools.services.errors import ValidationError


@pytest.fixture
def mock_client():
    """Create a mock NotebookLMClient."""
    client = MagicMock()
    client.list_notebooks.return_value = [
        MagicMock(
            id="nb-001",
            title="AI Research",
            source_count=3,
            url="",
            ownership="owned",
            is_shared=False,
            is_owned=True,
            created_at=None,
            modified_at=None,
        ),
        MagicMock(
            id="nb-002",
            title="Dev Tools",
            source_count=2,
            url="",
            ownership="owned",
            is_shared=False,
            is_owned=True,
            created_at=None,
            modified_at=None,
        ),
    ]
    client.query.return_value = {"answer": "OK", "conversation_id": None, "sources_used": []}
    return client


class TestBatchQuery:
    def test_query_all(self, mock_client):
        result = batch_query(mock_client, "test", all_notebooks=True)
        assert result["operation"] == "batch_query"
        assert result["total"] == 2
        assert result["succeeded"] == 2

    def test_query_by_name(self, mock_client):
        result = batch_query(mock_client, "test", notebook_names=["AI Research"])
        assert result["total"] == 1

    def test_empty_query_raises(self, mock_client):
        with pytest.raises(ValidationError):
            batch_query(mock_client, "")

    def test_partial_failure(self, mock_client):
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Failed")
            return {"answer": "OK", "conversation_id": None, "sources_used": []}

        mock_client.query.side_effect = side_effect
        result = batch_query(mock_client, "test", all_notebooks=True)
        assert result["succeeded"] == 1
        assert result["failed"] == 1


class TestBatchAddSource:
    def test_add_source_all(self, mock_client):
        with patch("notebooklm_tools.services.batch.sources_service") as mock_src:
            mock_src.add_source.return_value = {"source_id": "src-1", "message": "Added"}
            result = batch_add_source(mock_client, "https://example.com", all_notebooks=True)
            assert result["total"] == 2
            assert result["succeeded"] == 2

    def test_empty_url_raises(self, mock_client):
        with pytest.raises(ValidationError):
            batch_add_source(mock_client, "")


class TestBatchCreate:
    def test_create_multiple(self, mock_client):
        mock_nb = MagicMock()
        mock_nb.id = "new-1"
        mock_nb.title = "Project A"
        mock_nb.url = "https://notebooklm.google.com/notebook/new-1"
        mock_client.create_notebook.return_value = mock_nb

        result = batch_create(mock_client, ["Project A", "Project B"])
        assert result["total"] == 2
        assert result["operation"] == "batch_create"

    def test_empty_titles_raises(self, mock_client):
        with pytest.raises(ValidationError):
            batch_create(mock_client, [])


class TestBatchDelete:
    def test_delete_requires_confirm(self, mock_client):
        with pytest.raises(ValidationError):
            batch_delete(mock_client, notebook_names=["AI Research"], confirm=False)

    def test_delete_with_confirm(self, mock_client):
        mock_client.delete_notebook.return_value = True
        result = batch_delete(mock_client, notebook_names=["AI Research"], confirm=True)
        assert result["total"] == 1


class TestBatchStudio:
    def test_studio_all(self, mock_client):
        with patch("notebooklm_tools.services.batch.studio_service") as mock_studio:
            mock_studio.create_artifact.return_value = {"artifact_id": "art-1"}
            result = batch_studio(mock_client, "audio", all_notebooks=True)
            assert result["total"] == 2
            assert result["operation"] == "batch_studio"

    def test_no_targets(self, mock_client):
        mock_client.list_notebooks.return_value = []
        result = batch_studio(mock_client, "audio", all_notebooks=True)
        assert result["total"] == 0
