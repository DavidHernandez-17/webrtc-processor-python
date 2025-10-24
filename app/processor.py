import cv2
from aiortc import VideoStreamTrack
from vosk import Model, KaldiRecognizer
import os
from aiortc.mediastreams import MediaStreamTrack
import json
import time

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

        self._last_frame = frame 
        return frame

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
        self.track = track # El track de audio original de aiortc
        self.video_processor = video_processor # Referencia al procesador de video
        self.sio = sio_server # Referencia al servidor SocketIO para enviar comandos
        
        # Inicializar el reconocedor de Vosk
        self.recognizer = KaldiRecognizer(VOSK_MODEL, SAMPLE_RATE)

    async def recv(self):
        # 1. Recibir el frame de audio (chunk)
        frame = await self.track.recv()
        
        # 2. Convertir a formato de Vosk (16kHz mono)
        # aiortc usualmente entrega a 48kHz. Debemos convertirlo.
        # Aquí, por simplicidad, asumimos que el track ya viene en mono 16kHz,
        # pero en producción, puede necesitar resampleo (usando scipy, librosa, etc.).
        # Para aiortc + Vosk, a menudo se necesita forzar el formato adecuado.
        
        # Si el audio no viene en 16k, Vosk espera 16k.
        # Por ahora, simplemente tomaremos los bytes.
        
        chunk = frame.to_ndarray(format="s16")
        
        # El reconocedor de Vosk espera bytes
        audio_data = chunk.tobytes()

        # 3. Procesar el chunk de audio con Vosk
        if self.recognizer.AcceptWaveform(audio_data):
            result = json.loads(self.recognizer.Result())
            text = result.get('text', '').lower().strip()
            
            if text:
                print(f"🗣️ Comando Final Recibido: {text}")
                await self._process_command(text)
        else:
            partial_result = json.loads(self.recognizer.PartialResult())
            partial_text = partial_result.get('partial', '').lower().strip()
            if partial_text:
                print(f"🗣️ Parcial: {partial_text}")
                
        return frame

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