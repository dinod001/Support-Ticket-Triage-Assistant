import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import Base, get_db
from app.main import app
from app.services.llm_provider import MockLLMProvider
from app.services.rag_service import RAGService
from app.services.triage_service import TriageService

# Setup isolated test in-memory SQLite database with StaticPool so all threads share tables
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module", autouse=True)
def setup_test_app():
    """Initializes mock services on app.state before running API tests."""
    mock_provider = MockLLMProvider()
    app.state.provider = mock_provider
    app.state.triage_service = TriageService(provider=mock_provider)
    app.state.rag_service = RAGService(provider=mock_provider)
    # Ensure tables exist
    Base.metadata.create_all(bind=test_engine)
    yield


client = TestClient(app)


def test_health_check_endpoint():
    """Verifies that the /api/health endpoint responds with 200 OK."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "project" in data


def test_create_and_list_tickets():
    """
    Verifies assessment requirement:
    'one API test for creating and listing tickets'
    """
    # 1. Create Ticket
    payload = {
        "title": "Damaged package received for order #9921",
        "description": "My item arrived crushed and the box is open. Please process a refund.",
        "customer_email": "customer@example.com"
    }
    create_resp = client.post("/api/tickets", json=payload)
    assert create_resp.status_code == 201
    ticket_data = create_resp.json()

    assert ticket_data["id"] is not None
    assert ticket_data["status"] == "open"
    assert ticket_data["category"] == "Refund"
    assert ticket_data["priority"] == "high"
    assert "draft_reply" in ticket_data
    created_id = ticket_data["id"]

    # 2. List Tickets
    list_resp = client.get("/api/tickets")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(t["id"] == created_id for t in list_data["tickets"])

    # 3. Filter by Category
    filter_resp = client.get("/api/tickets?category=Refund")
    assert filter_resp.status_code == 200
    filter_data = filter_resp.json()
    assert all(t["category"] == "Refund" for t in filter_data["tickets"])


def test_get_and_patch_ticket():
    """Verifies viewing ticket details and updating draft reply and status."""
    # Create ticket
    payload = {
        "title": "Delivery inquiry for item",
        "description": "Where is my package? Tracking number is missing.",
        "customer_email": "jane@example.com"
    }
    create_resp = client.post("/api/tickets", json=payload)
    assert create_resp.status_code == 201
    ticket_id = create_resp.json()["id"]

    # GET ticket detail
    get_resp = client.get(f"/api/tickets/{ticket_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == ticket_id

    # PATCH ticket (agent edits draft reply and resolves ticket)
    update_payload = {
        "status": "resolved",
        "draft_reply": "Custom edited reply by human support agent.",
        "agent_notes": "Customer confirmed issue is resolved."
    }
    patch_resp = client.patch(f"/api/tickets/{ticket_id}", json=update_payload)
    assert patch_resp.status_code == 200
    updated_data = patch_resp.json()
    assert updated_data["status"] == "resolved"
    assert updated_data["draft_reply"] == "Custom edited reply by human support agent."
    assert updated_data["agent_notes"] == "Customer confirmed issue is resolved."


def test_ticket_not_found():
    """Verifies that querying a non-existent ticket returns 404."""
    response = client.get("/api/tickets/999999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_stream_draft_endpoint():
    """Verifies that the SSE streaming endpoint responds with text/event-stream."""
    # Create ticket
    payload = {
        "title": "Need help with return",
        "description": "How do I return my item within the 30 day window?"
    }
    create_resp = client.post("/api/tickets", json=payload)
    assert create_resp.status_code == 201
    ticket_id = create_resp.json()["id"]

    # Stream draft
    stream_resp = client.get(f"/api/tickets/{ticket_id}/stream-draft")
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers["content-type"]
    content = stream_resp.text
    assert "data:" in content
    assert '"done": true' in content
