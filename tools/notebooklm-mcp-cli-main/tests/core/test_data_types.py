from notebooklm_tools.core.data_types import (
    Collaborator,
    ConversationTurn,
    Notebook,
    ShareStatus,
)


def test_conversation_turn():
    turn = ConversationTurn(query="What is AI?", answer="AI is...", turn_number=1)
    assert turn.query == "What is AI?"


def test_collaborator():
    collab = Collaborator(email="test@example.com", role="editor")
    assert collab.role == "editor"


def test_share_status():
    status = ShareStatus(is_public=True, access_level="public", collaborators=[])
    assert status.is_public is True


def test_notebook_url():
    nb = Notebook(id="abc-123", title="Test", source_count=0, sources=[])
    assert nb.url == "https://notebooklm.google.com/notebook/abc-123"
