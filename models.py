"""
Local Lead Finder (Lite Edition) - Data Models
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import pandas as pd


@dataclass
class Lead:
    name: str
    phone: Optional[str] = None
    email: Optional[str] = "Pro Edition Only"
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    address: Optional[str] = None
    category: Optional[str] = None
    google_maps_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def to_dataframe(cls, leads: list["Lead"]) -> pd.DataFrame:
        if not leads:
            return pd.DataFrame(columns=[
                "name", "phone", "email", "website", "rating",
                "review_count", "address", "category", "google_maps_url"
            ])
        return pd.DataFrame([l.to_dict() for l in leads])
