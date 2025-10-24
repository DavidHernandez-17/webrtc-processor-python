import socketio
from .rtc import setup_webrtc_handlers, handle_ice

sio = socketio.AsyncClient()

handle_offer = setup_webrtc_handlers(sio)

def register_signaling_events():
    @sio.on("offer")
    async def on_offer(data):
        await handle_offer(data)

    @sio.on("ice-candidate")
    async def on_ice(data):
        await handle_ice(data)

    @sio.event
    async def connect():
        print("✅ Conectado al servidor de señalización")