from datetime import datetime, date, time
from sqlalchemy.orm import class_mapper

def to_dict_model(model, include_relationships=False, visited=None):
  if visited is None:
    visited = set()

  model_id = (type(model), getattr(model, 'id', id(model)))
  if model_id in visited:
    return None
  visited.add(model_id)

  data = {}

  for column in model.__table__.columns:
    value = getattr(model, column.name)
    if isinstance(value, (datetime, date, time)):
        data[column.name] = value.isoformat()
    else:
      data[column.name] = value

  if include_relationships:
    mapper = class_mapper(type(model))
    for relation in mapper.relationships:
      related_value = getattr(model, relation.key)
      if related_value is not None:
        if isinstance(related_value, list):
          data[relation.key] = [
            to_dict_model(item, include_relationships, visited)
            for item in related_value
          ]
        else:
          data[relation.key] = to_dict_model(
            related_value, include_relationships, visited
          )

  return data