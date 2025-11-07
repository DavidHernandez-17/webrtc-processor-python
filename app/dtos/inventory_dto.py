from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class InventoryDto:
  id: int
  property_id: int
  inventory_type_id: int
  event_id: int
  action: str
  synced: bool
  origin_id: int | None = None
  created_at: str | None = None
  updated_at: str | None = None
     
  @classmethod
  def from_model(cls, inventory):
    return cls(
      id=inventory.id,
      property_id=inventory.property_id,
      inventory_type_id=inventory.inventory_type_id,
      event_id=inventory.event_id,
      action=inventory.action,
      synced=inventory.synced,
      created_at=str(inventory.created_at) if inventory.created_at else None,
      updated_at=str(inventory.updated_at) if inventory.updated_at else None
    )
    
  def to_dict(self):
    return asdict(self)
  
  def to_json(self) -> Dict[str, Any]:
    return self.to_dict()