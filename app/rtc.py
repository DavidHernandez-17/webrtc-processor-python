from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from .processor import VideoProcessorTrack
from aiortc.sdp import candidate_from_sdp

pc = RTCPeerConnection()

@pc.on("connectionstatechange")
async def on_connectionstatechange():
    print("📡 Estado conexión:", pc.connectionState)

@pc.on("track")
def on_track(track):
    print(f"🎯 Track recibido: {track.kind}")
    if track.kind == "video":
        print("📹 Stream de video recibido (iniciando procesamiento)")
        processed_track = VideoProcessorTrack(track)
        pc.addTrack(processed_track)

async def handle_offer(data, sio):
    print("📥 Offer recibida")
    offer = RTCSessionDescription(sdp=data["sdp"]["sdp"], type=data["sdp"]["type"])
    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    await sio.emit("answer", {
        "targetId": data["senderId"],
        "sdp": {
            "type": pc.localDescription.type,
            "sdp": pc.localDescription.sdp
        }
    })

async def handle_ice(data):
    print("❄️ ICE recibido:", data)

    c = data.get("candidate", data)
    if not c:
        return

    try:
        parsed = candidate_from_sdp(c["candidate"])
        parsed.sdpMid = c.get("sdpMid")
        parsed.sdpMLineIndex = c.get("sdpMLineIndex")

        await pc.addIceCandidate(parsed)
        print("✅ ICE agregado correctamente")

    except Exception as e:
        print(f"⚠️ Error agregando ICE: {e}")