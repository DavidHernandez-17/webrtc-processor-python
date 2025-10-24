import cv2
from aiortc import VideoStreamTrack
from vosk import Model, KaldiRecognizer
import os
from aiortc.mediastreams import MediaStreamTrack, MediaStreamError
import json
import time
import asyncio

MODEL_PATH = "/usr/local/lib/python3.11/site-packages/vosk_model/vosk-model-small-es-0.42"

print(f"DEBUG: MODEL_PATH completo: {MODEL_PATH}")
print(f"DEBUG: ¿Existe el modelo? {os.path.isdir(MODEL_PATH)}")

SAMPLE_RATE = 16000

if not os.path.exists(MODEL_PATH):
    raise Exception(f"Modelo Vosk no encontrado en: {MODEL_PATH}. ¡Descárgalo y descomprímelo!")

try:
    VOSK_MODEL = Model(MODEL_PATH)
except Exception as e:
    print(f"Error cargando el modelo Vosk: {e}")
    VOSK_MODEL = None

class VideoProcessorTrack(VideoStreamTrack):
    def __init__(self, track):
        super().__init__()
        self.track = track
        self.count = 0
        self._last_frame = None

    async def recv(self):
        print("📹 Stream de video processor track")
        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")
        
        self.count += 1
        h, w, _ = img.shape
        
        cv2.circle(
            img, 
            (w // 2, h // 2),  # Centro del frame
            radius=10, 
            color=(0, 255, 0), # Verde (BGR)
            thickness=-1       # Relleno completo
        )
        
        print(f"📹 Procesando Frame #{self.count} | Video activo")

        self._last_frame = frame 
        return frame.from_ndarray(img, format="bgr24")

    async def capture_frame(self):
        """Captura el frame más reciente y lo guarda."""
        if self._last_frame is None:
            print("⚠️ No hay frames de video para capturar.")
            return None
        
        # Guarda la imagen usando un timestamp
        timestamp = int(time.time() * 1000)
        filename = f"capture_{timestamp}.jpg"
        
        # Convertir a formato legible por CV2 o PIL si es necesario
        # Si usas el frame crudo de aiortc, puedes usar frame.to_ndarray()
        
        # Ejemplo muy simple (ajustar según el formato de _last_frame)
        cv2_image = self._last_frame.to_ndarray(format="bgr24") 
        cv2.imwrite(filename, cv2_image)
        
        return filename
    
class AudioProcessorTrack(MediaStreamTrack):
    kind = "audio"
    
    def __init__(self, track, video_processor, sio_server):
        super().__init__()
        self.track = track
        self.video_processor = video_processor
        self.sio = sio_server
        self.last_pts = None
        
        self.stop_event = asyncio.Event()
        
        # Inicializar el reconocedor de Vosk
        self.recognizer = KaldiRecognizer(VOSK_MODEL, SAMPLE_RATE)
        asyncio.ensure_future(self._run_loop())

    async def _run_loop(self):
        print("🎧 AudioProcessorTrack: Iniciando loop de consumo de audio para Vosk.")
        audio_buffer = bytearray()
        
        while not self.stop_event.is_set():
            try:
                frame = await self.track.recv()
                
                if frame.pts == self.last_pts:
                    continue
                self.last_pts = frame.pts
                
                chunk = frame.to_ndarray(format="s16")
                audio_data = chunk.tobytes()
                
                if isinstance(audio_data, bytearray):
                    audio_data = bytes(audio_data)
                
                audio_buffer.extend(audio_data)

                if len(audio_buffer) > 16000 * 2 * 0.5:
                    buffer_to_process = bytes(audio_buffer)
                    if self.recognizer.AcceptWaveform(buffer_to_process):
                        result = json.loads(self.recognizer.Result())
                        text = result.get('text', '').lower().strip()
                        if text:
                            print(f"🗣️ Comando Final Recibido: {text}")
                            await self._process_command(text)
                        audio_buffer.clear()
                    else:
                        partial = json.loads(self.recognizer.PartialResult())
                        partial_text = partial.get('partial', '').lower().strip()
                        if partial_text:
                            print(f"🗣️ Parcial: {partial_text}")

            except MediaStreamError:
                break
            except Exception as e:
                print(f"🎧 Error crítico en loop de audio: {e}")
                break
        print("🎧 AudioProcessorTrack: Loop de consumo de audio finalizado.")

    def stop(self):
        """Método de limpieza para detener el bucle de consumo."""
        self.stop_event.set()

    async def _process_command(self, command):
        """Decide qué hacer con el comando de voz."""
        
        if any(keyword in command for keyword in ["tomar foto", "capturar", "saca foto", "fotografía"]):
            print("📸 Comando 'Tomar Foto' detectado.")
            # Llama al método de captura del procesador de video
            # Este método debe ser asíncrono en VideoProcessorTrack
            captured_image_path = await self.video_processor.capture_frame()
            
            if captured_image_path:
                print(f"✅ Foto capturada: {captured_image_path}")
                # Notifica a través de SocketIO si es necesario
                await self.sio.emit("command_executed", {"action": "photo_captured", "path": captured_image_path})
                
        # Puedes añadir más comandos aquí (ej. iniciar grabación, detener, etc.)
        elif "iniciar grabación" in command:
            print("🎬 Comando 'Iniciar Grabación' detectado.")
            await self.sio.emit("command_executed", {"action": "start_recording"})
            
    async def recv(self):
        """
        [CORRECCIÓN CRÍTICA] Este método debe existir porque 
        MediaStreamTrack lo declara como abstracto, pero no lo usamos 
        porque consumimos el frame en _run_loop.
        """
        raise NotImplementedError("AudioProcessorTrack solo consume datos, no los re-envía por recv().")