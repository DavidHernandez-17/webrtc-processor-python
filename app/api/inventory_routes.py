from aiohttp import web
import json
import traceback
from app.services.inventory_service import InventoryService

class InventoryAPI:
  def __init__(self, inventory_service: InventoryService):
    self.inventory_service = inventory_service
    
  def setup_routes(self, app: web.Application):
    app.router.add_get("/", lambda request: web.json_response({"status": "ok"}))
    app.router.add_post('/api/v1/inventory/enter', self.enter_inventory)
    app.router.add_get('/api/v1/inventory', self.get_inventories)
    
  async def enter_inventory(self, request: web.Request) -> web.Response:
    try:
      data = await request.json()
    except json.JSONDecodeError:
      return web.json_response({
        "success": False,
        "error": "Invalid JSON"
      }, status=400)
      
    required_fields = ['property_id', 'inventory_type_id', 'event_id']
    missing_fields = [f for f in required_fields if f not in data]
    
    if missing_fields:
      return web.json_response({
        "success": False,
        "error": f"Missing required fields: {', '.join(missing_fields)}"
      }, status=400)
      
    try:
      property_id = data['property_id']
      inventory_type_id = data['inventory_type_id']
      event_id = data['event_id']
      
      inventory = self.inventory_service.enter_inventory(
        property_id, inventory_type_id, event_id
      )

      return web.json_response({
        "success": True,
        "inventory": inventory,
        "metadata": {
          "property_id": property_id,
          "inventory_type_id": inventory_type_id,
          "event_id": event_id
        }
      })
    except Exception as e:
      print("❌ Error en enter_inventory:", str(e))
      traceback.print_exc()
      return web.json_response({
        "success": False,
        "error": str(e)
      }, status=500)
      
  async def get_inventories(self) -> web.Response:
    try:
      inventories = self.inventory_service.get_inventories()
      
      return web.json_response({
        "success": True,
        "inventories": inventories,
        "count": len(inventories)
      })
    except Exception as e:
      print("❌ Error en get_inventories:", str(e))
      traceback.print_exc()
      return web.json_response({
        "success": False,
        "error": str(e)
      }, status=500)