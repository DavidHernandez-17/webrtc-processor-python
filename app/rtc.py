from aiortc import RTCPeerConnection, RTCSessionDescription
from .processor import VideoProcessorTrack, AudioProcessorTrack
from aiortc.sdp import candidate_from_sdp
import asyncio

# Variables globales
pc = RTCPeerConnection()
video_processor_instance = None
audio_processor_instance = None
video_track_ready = asyncio.Event()
pending_audio_track = None


async def _consume_video_frames(video_processor):
    """Consume frames continuamente del video processor para mantenerlo activo."""
    frame_count = 0
    try:
        print("🎬 Iniciando consumo de frames de video...")
        while True:
            frame = await video_processor.recv()
            frame_count += 1
            
            # Log cada 300 frames (~10 segundos a 30fps)
            if frame_count % 300 == 0:
                print(f"📹 {frame_count} frames procesados")
            
    except Exception as e:
        print(f"🔚 Fin del consumo de video: {e}")
        print(f"📊 Total frames procesados: {frame_count}")


async def initialize_audio_processor(audio_track, sio_server):
    """Espera al video processor y luego inicializa el audio processor."""
    global video_processor_instance, audio_processor_instance
    
    print("⏳ Esperando a que el video processor esté listo...")
    # Esperar máximo 5 segundos a que llegue el video track
    try:
        await asyncio.wait_for(video_track_ready.wait(), timeout=5.0)
        print("✅ Video processor listo, inicializando audio processor...")
    except asyncio.TimeoutError:
        print("⚠️ Timeout esperando video track, continuando sin él...")
    
    audio_processor_instance = AudioProcessorTrack(
        track=audio_track,
        video_processor=video_processor_instance,
        sio_server=sio_server
    )
    print("✅ Audio processor inicializado correctamente")


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
    global pending_audio_track
    global video_track_ready

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("📡 Estado conexión:", pc.connectionState)
        if pc.connectionState == "closed":
            global audio_processor_instance
            if audio_processor_instance:
                audio_processor_instance.stop()
            # Reset de eventos
            video_track_ready.clear()

    @pc.on("track")
    def on_track(track):
        global video_processor_instance
        global audio_processor_instance
        global pending_audio_track
        
        print(f"🎯 Track recibido: {track.kind}")
        
        if track.kind == "video":
            print("📹 Stream de video recibido (iniciando procesamiento)")
            video_processor_instance = VideoProcessorTrack(track)
            
            # IMPORTANTE: Añadir el video processor al PeerConnection
            # para que recv() sea llamado y capture frames
            pc.addTrack(video_processor_instance)
            
            # Iniciar tarea para consumir frames continuamente
            asyncio.create_task(_consume_video_frames(video_processor_instance))
            
            # Señalar que el video está listo
            video_track_ready.set()
            print("✅ Video processor listo")
            
            # Si el audio llegó primero, inicializarlo ahora
            if pending_audio_track is not None:
                print("🎧 Inicializando audio processor pendiente...")
                asyncio.create_task(
                    initialize_audio_processor(pending_audio_track, sio_server)
                )
                pending_audio_track = None
        
        elif track.kind == "audio":
            print("🎧 Stream de audio recibido")
            
            # Si el video ya está listo, inicializar inmediatamente
            if video_processor_instance is not None:
                print("✅ Video ya disponible, inicializando audio processor...")
                asyncio.create_task(
                    initialize_audio_processor(track, sio_server)
                )
            else:
                # Si no, guardar el track para inicializarlo cuando llegue el video
                print("⏳ Video aún no disponible, guardando audio track...")
                pending_audio_track = track
                asyncio.create_task(
                    initialize_audio_processor(track, sio_server)
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
        print("📤 Answer enviada")
    
    return handle_offer_closure