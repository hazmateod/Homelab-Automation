"""
Asset relationship model.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AssetRelationship:
    source_type: str
    source_id: str
    relationship_type: str
    target_type: str
    target_id: str
