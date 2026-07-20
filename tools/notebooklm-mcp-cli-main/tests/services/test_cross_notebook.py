"""Tests for cross_notebook service — cross-notebook queries."""

from unittest.mock import MagicMock, patch

import pytest

from notebooklm_tools.services.cross_notebook import (
    _query_single_notebook,
    _resolve_notebook_ids,
    cross_notebook_query,
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
        MagicMock(
            id="nb-003",
            title="Courses",
            source_count=1,
            url="",
            ownership="owned",
            is_shared=False,
            is_owned=True,
            created_at=None,
            modified_at=None,
        ),
    ]
    client.query.return_value = {
        "answer": "Test answer",
        "conversation_id": "conv-1",
        "sources_used": [{"id": "src-1", "title": "Source 1"}],
    }
    return client


class TestQuerySingleNotebook:
    def test_successful_query(self, mock_client):
        result = _query_single_notebook(mock_client, "nb-001", "AI Research", "test query")
        assert result["notebook_id"] == "nb-001"
        assert result["notebook_title"] == "AI Research"
        assert result["answer"] == "Test answer"
        assert result["error"] is None

    def test_failed_query_returns_error(self, mock_client):
        mock_client.query.side_effect = Exception("API error")
        result = _query_single_notebook(mock_client, "nb-001", "AI Research", "test query")
        assert result["error"] is not None
        assert result["answer"] == ""


class TestResolveNotebookIds:
    def test_resolve_all_notebooks(self, mock_client):
        result = _resolve_notebook_ids(mock_client, all_notebooks=True)
        assert len(result) == 3
        assert result[0] == ("nb-001", "AI Research")

    def test_resolve_by_name(self, mock_client):
        result = _resolve_notebook_ids(mock_client, notebook_names=["AI Research"])
        assert len(result) == 1
        assert result[0] == ("nb-001", "AI Research")

    def test_resolve_by_name_case_insensitive(self, mock_client):
        result = _resolve_notebook_ids(mock_client, notebook_names=["ai research"])
        assert len(result) == 1
        assert result[0] == ("nb-001", "AI Research")

    def test_resolve_by_id_fallback(self, mock_client):
        result = _resolve_notebook_ids(mock_client, notebook_names=["some-uuid"])
        assert len(result) == 1
        assert result[0] == ("some-uuid", "some-uuid")

    @patch("notebooklm_tools.services.cross_notebook.smart_select_service")
    def test_resolve_by_tags(self, mock_ss, mock_client):
        mock_ss.smart_select.return_value = {
            "query": "ai",
            "matched_notebooks": [
                {"notebook_id": "nb-001", "notebook_title": "AI Research", "tags": ["ai"]},
            ],
            "count": 1,
        }
        result = _resolve_notebook_ids(mock_client, tags=["ai"])
        assert len(result) == 1
        assert result[0] == ("nb-001", "AI Research")

    def test_no_selection_raises(self, mock_client):
        with pytest.raises(ValidationError):
            _resolve_notebook_ids(mock_client)


class TestCrossNotebookQuery:
    def test_query_all_notebooks(self, mock_client):
        result = cross_notebook_query(mock_client, "test query", all_notebooks=True)
        assert result["query"] == "test query"
        assert result["notebooks_queried"] == 3
        assert result["notebooks_succeeded"] == 3
        assert result["notebooks_failed"] == 0
        assert len(result["results"]) == 3

    def test_query_specific_notebooks(self, mock_client):
        result = cross_notebook_query(
            mock_client,
            "test query",
            notebook_names=["AI Research", "Dev Tools"],
        )
        assert result["notebooks_queried"] == 2

    def test_empty_query_raises(self, mock_client):
        with pytest.raises(ValidationError):
            cross_notebook_query(mock_client, "")

    def test_whitespace_query_raises(self, mock_client):
        with pytest.raises(ValidationError):
            cross_notebook_query(mock_client, "   ")

    def test_partial_failures(self, mock_client):
        call_count = [0]
        success_response = {
            "answer": "OK",
            "conversation_id": None,
            "sources_used": [],
        }

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Rate limited")
            return success_response

        mock_client.query.side_effect = side_effect

        result = cross_notebook_query(mock_client, "test query", all_notebooks=True)
        assert result["notebooks_queried"] == 3
        assert result["notebooks_succeeded"] == 2
        assert result["notebooks_failed"] == 1

    def test_results_sorted_success_first(self, mock_client):
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Failed")
            return {"answer": "OK", "conversation_id": None, "sources_used": []}

        mock_client.query.side_effect = side_effect

        result = cross_notebook_query(mock_client, "test query", all_notebooks=True)
        # Successful results should come first
        errors = [r for r in result["results"] if r["error"] is not None]
        successes = [r for r in result["results"] if r["error"] is None]
        assert len(successes) == 2
        assert len(errors) == 1
        # Errors should be at the end
        assert result["results"][-1]["error"] is not None

    def test_no_matching_notebooks(self, mock_client):
        mock_client.list_notebooks.return_value = []
        result = cross_notebook_query(mock_client, "test query", all_notebooks=True)
        assert result["notebooks_queried"] == 0
        assert result["results"] == []

    def test_max_concurrent_limits_threads(self, mock_client):
        result = cross_notebook_query(
            mock_client,
            "test query",
            all_notebooks=True,
            max_concurrent=1,
        )
        assert result["notebooks_queried"] == 3
        assert result["notebooks_succeeded"] == 3
