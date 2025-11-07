import asyncio
from aiohttp import web

from .signaling import sio, register_signaling_events
from app.api.inventory_routes import InventoryAPI
from app.services.inventory_service import InventoryService

async def init_app():
    app = web.Application()

    inventory_service = InventoryService()
    inventory_api = InventoryAPI(inventory_service)
    inventory_api.setup_routes(app)
    
    register_signaling_events()
    
    return app

async def main():
    app = await init_app()
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("✅ API HTTP lista en http://localhost:8080")
    
    try:
        print("🔌 Conectando al servidor de signaling...")
        await sio.connect("http://host.docker.internal:3000")
    except Exception as e:
        print(f"❌ Error al conectar con signaling: {e}")
    
    await sio.wait()

if __name__ == "__main__":
    asyncio.run(main())
