"""Tests for pipeline service — multi-step workflow automation."""

from unittest.mock import MagicMock, patch

import pytest

from notebooklm_tools.services.errors import ValidationError
from notebooklm_tools.services.pipeline import (
    _load_pipeline,
    _substitute_vars,
    pipeline_create,
    pipeline_list,
    pipeline_run,
)


@pytest.fixture
def mock_client():
    """Create a mock NotebookLMClient."""
    client = MagicMock()
    return client


@pytest.fixture
def pipelines_dir(tmp_path):
    """Provide a temporary pipelines directory."""
    with patch("notebooklm_tools.services.pipeline.get_storage_dir", return_value=tmp_path):
        yield tmp_path


class TestSubstituteVars:
    def test_substitute_single_var(self):
        result = _substitute_vars(
            {"url": "$INPUT_URL", "type": "url"},
            {"INPUT_URL": "https://example.com"},
        )
        assert result["url"] == "https://example.com"
        assert result["type"] == "url"

    def test_no_substitution_needed(self):
        result = _substitute_vars({"query": "hello"}, {})
        assert result["query"] == "hello"

    def test_missing_variable_kept_as_is(self):
        result = _substitute_vars({"url": "$MISSING"}, {})
        assert result["url"] == "$MISSING"


class TestLoadPipeline:
    def test_load_builtin(self):
        result = _load_pipeline("ingest-and-podcast")
        assert result is not None
        assert result["name"] == "ingest-and-podcast"
        assert len(result["steps"]) == 3

    def test_load_user_defined(self, pipelines_dir):
        import yaml

        pipeline_def = {
            "name": "custom",
            "description": "Custom pipeline",
            "steps": [{"action": "notebook_query", "params": {"query": "test"}}],
        }
        pipeline_file = pipelines_dir / "pipelines" / "custom.yaml"
        pipeline_file.parent.mkdir(parents=True, exist_ok=True)
        pipeline_file.write_text(yaml.dump(pipeline_def))

        result = _load_pipeline("custom")
        assert result is not None
        assert result["name"] == "custom"

    def test_load_nonexistent(self, pipelines_dir):
        result = _load_pipeline("nonexistent")
        assert result is None


class TestPipelineList:
    def test_list_includes_builtins(self, pipelines_dir):
        result = pipeline_list()
        names = [p["name"] for p in result]
        assert "ingest-and-podcast" in names
        assert "research-and-report" in names
        assert "multi-format" in names

    def test_list_includes_user_defined(self, pipelines_dir):
        import yaml

        pipeline_dir = pipelines_dir / "pipelines"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        (pipeline_dir / "my-pipeline.yaml").write_text(
            yaml.dump(
                {
                    "name": "my-pipeline",
                    "description": "My custom pipeline",
                    "steps": [{"action": "notebook_query", "params": {"query": "test"}}],
                }
            )
        )

        result = pipeline_list()
        names = [p["name"] for p in result]
        assert "my-pipeline" in names

        user_pipeline = next(p for p in result if p["name"] == "my-pipeline")
        assert user_pipeline["source"] == "user"


class TestPipelineCreate:
    def test_create_valid(self, pipelines_dir):
        result = pipeline_create(
            "my-pipeline",
            "A test pipeline",
            [{"action": "notebook_query", "params": {"query": "test"}}],
        )
        assert result["name"] == "my-pipeline"
        assert result["steps_count"] == 1
        assert result["source"] == "user"

    def test_create_empty_name_raises(self, pipelines_dir):
        with pytest.raises(ValidationError):
            pipeline_create("", "desc", [{"action": "notebook_query"}])

    def test_create_no_steps_raises(self, pipelines_dir):
        with pytest.raises(ValidationError):
            pipeline_create("test", "desc", [])

    def test_create_invalid_action_raises(self, pipelines_dir):
        with pytest.raises(ValidationError):
            pipeline_create("test", "desc", [{"action": "invalid_action"}])

    def test_cannot_overwrite_builtin(self, pipelines_dir):
        with pytest.raises(ValidationError):
            pipeline_create("ingest-and-podcast", "desc", [{"action": "notebook_query"}])


class TestPipelineRun:
    @patch("notebooklm_tools.services.pipeline.chat_service")
    def test_run_single_step(self, mock_chat, mock_client, pipelines_dir):
        mock_chat.query.return_value = {"answer": "OK", "conversation_id": None, "sources_used": []}

        # Create a simple user pipeline
        import yaml

        pipeline_dir = pipelines_dir / "pipelines"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        (pipeline_dir / "simple.yaml").write_text(
            yaml.dump(
                {
                    "name": "simple",
                    "steps": [{"action": "notebook_query", "params": {"query": "test"}}],
                }
            )
        )

        result = pipeline_run(mock_client, "nb-001", "simple")
        assert result["pipeline_name"] == "simple"
        assert result["succeeded"] == 1
        assert result["failed"] == 0

    def test_run_nonexistent_raises(self, mock_client, pipelines_dir):
        with pytest.raises(ValidationError):
            pipeline_run(mock_client, "nb-001", "nonexistent")

    @patch("notebooklm_tools.services.pipeline.chat_service")
    def test_run_stops_on_failure(self, mock_chat, mock_client, pipelines_dir):
        mock_chat.query.side_effect = Exception("API error")

        import yaml

        pipeline_dir = pipelines_dir / "pipelines"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        (pipeline_dir / "two-step.yaml").write_text(
            yaml.dump(
                {
                    "name": "two-step",
                    "steps": [
                        {"action": "notebook_query", "params": {"query": "step1"}},
                        {"action": "notebook_query", "params": {"query": "step2"}},
                    ],
                }
            )
        )

        result = pipeline_run(mock_client, "nb-001", "two-step")
        assert result["failed"] == 1
        assert result["total_steps"] == 2
        assert len(result["steps"]) == 1  # stopped after first failure

    @patch("notebooklm_tools.services.pipeline.notebooks_service")
    def test_run_notebook_delete_action(self, mock_notebooks, mock_client, pipelines_dir):
        mock_notebooks.delete_notebook.return_value = {"deleted": True}

        import yaml

        pipeline_dir = pipelines_dir / "pipelines"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        (pipeline_dir / "delete-test.yaml").write_text(
            yaml.dump(
                {
                    "name": "delete-test",
                    "steps": [{"action": "notebook_delete", "params": {}}],
                }
            )
        )

        result = pipeline_run(mock_client, "nb-001", "delete-test")
        assert result["succeeded"] == 1
        mock_notebooks.delete_notebook.assert_called_once_with(mock_client, "nb-001")

    @patch("notebooklm_tools.services.pipeline.chat_service")
    def test_run_with_variables(self, mock_chat, mock_client, pipelines_dir):
        mock_chat.query.return_value = {"answer": "OK", "conversation_id": None, "sources_used": []}

        import yaml

        pipeline_dir = pipelines_dir / "pipelines"
        pipeline_dir.mkdir(parents=True, exist_ok=True)
        (pipeline_dir / "var-test.yaml").write_text(
            yaml.dump(
                {
                    "name": "var-test",
                    "steps": [{"action": "notebook_query", "params": {"query": "$MY_QUERY"}}],
                }
            )
        )

        result = pipeline_run(
            mock_client,
            "nb-001",
            "var-test",
            variables={"MY_QUERY": "What is AI?"},
        )
        assert result["succeeded"] == 1
        mock_chat.query.assert_called_once()
