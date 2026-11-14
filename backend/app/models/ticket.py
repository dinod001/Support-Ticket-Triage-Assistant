from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from app.core.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    customer_email = Column(String(255), nullable=True)

    # Status: 'open', 'in_progress', 'resolved', 'closed'
    status = Column(String(50), default="open", index=True, nullable=False)

    # AI Triage Fields
    category = Column(String(50), index=True, nullable=True)
    priority = Column(String(20), index=True, nullable=True)  # 'low', 'medium', 'high', 'urgent'
    sentiment = Column(String(20), nullable=True)  # 'positive', 'neutral', 'negative', 'frustrated'
    summary = Column(Text, nullable=True)
    entities = Column(JSON, default=dict, nullable=False)  # {"order_number": "...", "product": "..."}

    # RAG Generated Draft & Citations
    draft_reply = Column(Text, nullable=True)
    cited_articles = Column(JSON, default=list, nullable=False)  # ["Damaged or Defective Items Policy"]

    # Support Agent Review
    agent_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} title='{self.title[:30]}' status='{self.status}' category='{self.category}'>"
