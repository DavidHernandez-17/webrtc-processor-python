from aiortc import RTCPeerConnection, RTCSessionDescription
from .processor import VideoProcessorTrack, AudioProcessorTrack
from aiortc.sdp import candidate_from_sdp

pc = RTCPeerConnection()
video_processor_instance = None
audio_processor_instance = None

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
        
def setup_webrtc_handlers(sio_server):
    global pc
    global video_processor_instance

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("📡 Estado conexión:", pc.connectionState)
        if pc.connectionState == "closed":
            global audio_processor_instance
            if audio_processor_instance:
                audio_processor_instance.stop()

    @pc.on("track")
    def on_track(track):
        global video_processor_instance
        global audio_processor_instance
        
        print(f"🎯 Track recibido: {track.kind}")
        
        if track.kind == "video":
            print("📹 Stream de video recibido (iniciando procesamiento)")
            video_processor_instance = VideoProcessorTrack(track)
        
        elif track.kind == "audio":
            print("🎧 Stream de audio recibido (iniciando reconocimiento de voz)")
            if video_processor_instance is None:
                print("⚠️ Advertencia: El track de video aún no se ha inicializado...")

            audio_processor_instance = AudioProcessorTrack(
                track=track, 
                video_processor=video_processor_instance,
                sio_server=sio_server
            )

    async def handle_offer_closure(data):
        print("📥 Offer recibida")
        offer = RTCSessionDescription(sdp=data["sdp"]["sdp"], type=data["sdp"]["type"])
        await pc.setRemoteDescription(offer)

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        await sio_server.emit("answer", {
            "targetId": data["senderId"],
            "sdp": {
                "type": pc.localDescription.type,
                "sdp": pc.localDescription.sdp
            }
        })
    
    return handle_offer_closure