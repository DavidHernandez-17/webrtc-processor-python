from aiortc import RTCPeerConnection, RTCSessionDescription
from .processor import VideoProcessorTrack

pc = RTCPeerConnection()

@pc.on("track")
def on_track(track):
    if track.kind == "video":
        print("📹 Stream de video recibido")
        pc.addTrack(VideoProcessorTrack(track))

async def handle_offer(data, sio):
    print("📥 Offer recibida")
    offer = RTCSessionDescription(sdp=data["sdp"]["sdp"], type=data["sdp"]["type"])
    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # Enviar la respuesta al móvil a través de NestJS
    sio.emit("answer", {
        "targetId": data["senderId"],
        "sdp": {
            "type": pc.localDescription.type,
            "sdp": pc.localDescription.sdp
        }
    })

async def handle_ice(data):
    print("❄️ ICE recibido")
    candidate = data["candidate"]
    await pc.addIceCandidate(candidate)
