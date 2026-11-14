import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.database import Base, init_db
from app.models.ticket import Ticket
from app.models.llm_log import LLMLog
from app.schemas.triage import TriageResult
from app.schemas.ticket import TicketCreate, TicketResponse


def test_verification():
    print("=" * 60)
    print("1. Checking Settings...")
    print(f"   Project: {settings.PROJECT_NAME}")
    print(f"   LLM Provider: {settings.LLM_PROVIDER}")
    print(f"   Ollama Model: {settings.OLLAMA_CHAT_MODEL}")
    assert settings.PROJECT_NAME == "Support Ticket Triage Assistant"
    print("   [OK] Settings loaded successfully!")

    print("\n2. Checking Database Schema & In-Memory SQLite Table Creation...")
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    init_db(target_engine=test_engine)
    TestSession = sessionmaker(bind=test_engine)
    session = TestSession()

    # Create a dummy ticket
    sample_ticket = Ticket(
        title="Order arrived with broken screen",
        description="I ordered a laptop monitor and the box arrived damaged and screen broken.",
        customer_email="customer@example.com",
        category="Refund",
        priority="high",
        sentiment="frustrated",
        summary="Customer received a broken monitor and demands refund.",
        entities={"order_number": "ORD-12345", "product": "laptop monitor"},
        draft_reply="Dear customer, we are very sorry. Under our Damaged Items Policy, please provide photos within 48h.",
        cited_articles=["Damaged or Defective Items Policy"]
    )
    session.add(sample_ticket)
    session.commit()
    session.refresh(sample_ticket)

    assert sample_ticket.id == 1
    assert sample_ticket.status == "open"
    assert sample_ticket.entities["order_number"] == "ORD-12345"
    print(f"   [OK] Ticket created in DB with ID: {sample_ticket.id}, Status: {sample_ticket.status}")

    # Create an LLM Log
    log = LLMLog(
        ticket_id=sample_ticket.id,
        call_type="triage",
        model_name="qwen2.5:1.5b",
        latency_ms=1450,
        success=True
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    assert log.id == 1
    assert log.success is True
    print(f"   [OK] LLMLog created with ID: {log.id}, Latency: {log.latency_ms}ms")

    print("\n3. Checking Pydantic Schema Validation (TriageResult)...")
    valid_triage_data = {
        "category": "Refund",
        "priority": "high",
        "sentiment": "negative",
        "summary": "Customer requesting a refund for damaged goods.",
        "entities": {"order_number": "ORD-9988"}
    }
    triage_obj = TriageResult(**valid_triage_data)
    assert triage_obj.category == "Refund"
    assert triage_obj.entities["order_number"] == "ORD-9988"
    print(f"   [OK] TriageResult parsed and validated: {triage_obj.model_dump()}")

    print("\n4. Checking Ticket Serialization Schema...")
    ticket_dict = {
        "id": sample_ticket.id,
        "title": sample_ticket.title,
        "description": sample_ticket.description,
        "customer_email": sample_ticket.customer_email,
        "status": sample_ticket.status,
        "category": sample_ticket.category,
        "priority": sample_ticket.priority,
        "sentiment": sample_ticket.sentiment,
        "summary": sample_ticket.summary,
        "entities": sample_ticket.entities,
        "draft_reply": sample_ticket.draft_reply,
        "cited_articles": sample_ticket.cited_articles,
        "agent_notes": sample_ticket.agent_notes,
        "created_at": sample_ticket.created_at,
        "updated_at": sample_ticket.updated_at
    }
    ticket_resp = TicketResponse.model_validate(ticket_dict)
    assert ticket_resp.id == 1
    print(f"   [OK] TicketResponse schema valid: ID {ticket_resp.id}")

    session.close()
    print("\n" + "=" * 60)
    print("ALL TESTS & VERIFICATIONS PASSED 100% SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    test_verification()
