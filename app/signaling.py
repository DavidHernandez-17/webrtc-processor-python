import socketio
from .rtc import handle_offer, handle_ice

sio = socketio.Client()

def register_signaling_events():
    @sio.on("offer")
    async def on_offer(data):
        await handle_offer(data, sio)

    @sio.on("ice-candidate")
    async def on_ice(data):
        await handle_ice(data)
