#!/usr/bin/env python3
"""ExportMixin - Export artifacts to Google Docs/Sheets.

This mixin provides export operations for NotebookLM artifacts:
- export_artifact: Generic export to Docs or Sheets
- export_data_table_to_sheets: Export Data Table → Google Sheets
- export_report_to_docs: Export Report → Google Docs
"""

from typing import Any

from . import constants
from .base import BaseClient


class ExportMixin(BaseClient):
    """Mixin providing export operations to Google Docs/Sheets.

    This class inherits from BaseClient and provides artifact export
    functionality. It is designed to be used with multiple inheritance
    in the final NotebookLMClient class.
    """

    def export_artifact(
        self,
        notebook_id: str,
        artifact_id: str,
        title: str = "NotebookLM Export",
        export_type: str = "docs",
        content: str | None = None,
    ) -> dict[str, Any]:
        """Export an artifact to Google Docs or Sheets.

        Args:
            notebook_id: The notebook UUID
            artifact_id: The artifact UUID to export
            title: Title for the exported document
            export_type: "docs" or "sheets"
            content: Optional content override (for note exports)

        Returns:
            Dict with export result including:
            - status: "success" or "failed"
            - url: URL of created document (if successful)
            - message: Human-readable message

        Raises:
            ValueError: If export_type is invalid
        """
        export_type_code = constants.EXPORT_TYPES.get_code(export_type)

        # RPC params: [None, artifact_id, content, title, export_type_code]
        params = [None, artifact_id, content, title, export_type_code]

        result = self._call_rpc(
            self.RPC_EXPORT_ARTIFACT,
            params,
            f"/notebook/{notebook_id}",
        )

        return self._parse_export_result(result)

    def export_data_table_to_sheets(
        self,
        notebook_id: str,
        artifact_id: str,
        title: str = "Data Table Export",
    ) -> dict[str, Any]:
        """Export a Data Table artifact to Google Sheets.

        Args:
            notebook_id: The notebook UUID
            artifact_id: The Data Table artifact UUID
            title: Title for the created spreadsheet

        Returns:
            Dict with export result including document URL
        """
        return self.export_artifact(
            notebook_id=notebook_id,
            artifact_id=artifact_id,
            title=title,
            export_type="sheets",
        )

    def export_report_to_docs(
        self,
        notebook_id: str,
        artifact_id: str,
        title: str = "Report Export",
    ) -> dict[str, Any]:
        """Export a Report artifact to Google Docs.

        Works with all report types: Briefing Doc, Study Guide, Blog Post, etc.

        Args:
            notebook_id: The notebook UUID
            artifact_id: The Report artifact UUID
            title: Title for the created document

        Returns:
            Dict with export result including document URL
        """
        return self.export_artifact(
            notebook_id=notebook_id,
            artifact_id=artifact_id,
            title=title,
            export_type="docs",
        )

    def _parse_export_result(self, result: Any) -> dict[str, Any]:
        """Parse export RPC response.

        Expected response structure varies, but URL is typically nested:
        - Simple: [[[url]], ...]
        - Or: [[url], ...]

        Args:
            result: Raw RPC response

        Returns:
            Parsed result dict with status, url, and message
        """
        doc_url = None

        if result and isinstance(result, list):
            # Try to extract URL from nested response
            # Pattern 1: [[[url]]]
            if len(result) > 0 and isinstance(result[0], list):
                if len(result[0]) > 0 and isinstance(result[0][0], list):
                    if result[0][0]:
                        doc_url = result[0][0][0]
                # Pattern 2: [[url]]
                elif len(result[0]) > 0 and isinstance(result[0][0], str):
                    doc_url = result[0][0]
            # Pattern 3: [url]
            elif len(result) > 0 and isinstance(result[0], str):
                doc_url = result[0]

        if doc_url:
            return {
                "status": "success",
                "url": doc_url,
                "message": f"Exported to: {doc_url}",
            }
        else:
            return {
                "status": "failed",
                "url": None,
                "message": "Export failed - no document URL returned",
            }
