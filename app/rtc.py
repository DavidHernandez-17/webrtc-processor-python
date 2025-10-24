from aiortc import RTCPeerConnection, RTCSessionDescription
from .processor import VideoProcessorTrack, AudioProcessorTrack
from aiortc.sdp import candidate_from_sdp

pc = RTCPeerConnection()
video_processor_instance = None

@pc.on("connectionstatechange")
async def on_connectionstatechange():
    print("📡 Estado conexión:", pc.connectionState)

@pc.on("track")
def on_track(track):
    global video_processor_instance
    print(f"🎯 Track recibido: {track.kind}")
    
    if track.kind == "video":
        print("📹 Stream de video recibido (iniciando procesamiento)")
        video_processor_instance = VideoProcessorTrack(track)
        # pc.addTrack(video_processor_instance)
    
    elif track.kind == "audio":
        print("🎧 Stream de audio recibido (iniciando reconocimiento de voz)")
        if video_processor_instance is None:
            print("⚠️ Advertencia: El track de video aún no se ha inicializado. El reconocimiento de voz no podrá capturar fotos.")

        audio_processor_instance = AudioProcessorTrack(
            track=track, 
            video_processor=video_processor_instance,
            sio_server=sio # ⬅️ Asegúrate de que 'sio' sea accesible aquí
        )
        # pc.addTrack(audio_processor_instance)

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