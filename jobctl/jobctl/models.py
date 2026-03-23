from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Listing:
    id: str
    company: str
    title: str
    url: Optional[str]
    description: Optional[str]
    location: Optional[str]
    salary: Optional[str]
    source: str
    status: str  # pending_review|accepted|dismissed|applied|interviewing|rejected|offered
    score: float
    notes: Optional[str]
    created_at: str
    updated_at: str


@dataclass
class Material:
    id: str
    listing_id: str
    type: str  # cv|cover_letter
    content: str
    created_at: str


@dataclass
class Calibration:
    id: str
    listing_id: str
    action: str  # accept|dismiss
    created_at: str
