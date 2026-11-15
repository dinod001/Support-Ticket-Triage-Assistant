from typing import Dict, Optional

from pydantic import BaseModel, Field


class TriageResult(BaseModel):
    category: str = Field(
        description="Ticket category, e.g., 'Technical', 'Refund', 'Shipping', 'Account', 'Damaged', or 'Billing'"
    )
    priority: str = Field(
        description="Assessed priority level: 'low', 'medium', 'high', or 'urgent'"
    )
    sentiment: str = Field(
        description="Detected customer sentiment: 'positive', 'neutral', 'negative', or 'frustrated'"
    )
    summary: str = Field(
        description="One-sentence executive summary of the customer's inquiry or issue"
    )
    entities: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Extracted key entities, such as order_number, tracking_id, product_name, email"
    )
