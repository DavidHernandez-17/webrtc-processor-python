import cv2
from aiortc import VideoStreamTrack
from vosk import Model, KaldiRecognizer
import os
from aiortc.mediastreams import MediaStreamTrack, MediaStreamError
import json
import time
import asyncio

import wave
import tempfile

MODEL_PATH = "/usr/local/lib/python3.11/site-packages/vosk_model/vosk-model-small-es-0.42"
print(f"DEBUG: ¿Existe el modelo? {os.path.isdir(MODEL_PATH)}")

SAMPLE_RATE = 16000

if not os.path.exists(MODEL_PATH):
    raise Exception(f"Modelo Vosk no encontrado en: {MODEL_PATH}. ¡Descárgalo y descomprímelo!")

try:
    VOSK_MODEL = Model(MODEL_PATH)
    print("✅ Modelo Vosk cargado correctamente.")
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
        
        # Dibujar indicador verde (centro)
        h, w, _ = img.shape
        cv2.circle(img, (w // 2, h // 2), 10, (0, 255, 0), -1)
        self._last_frame = frame

        print(f"📹 Frame #{self.count} procesado.")
        return frame.from_ndarray(img, format="bgr24")

    async def capture_frame(self):
        """Captura el último frame recibido del video."""
        if self._last_frame is None:
            print("⚠️ No hay frames de video para capturar.")
            return None
        
        # Guarda la imagen usando un timestamp
        timestamp = int(time.time() * 1000)
        filename = f"capture_{timestamp}.jpg"

        cv2_image = self._last_frame.to_ndarray(format="bgr24")
        cv2.imwrite(filename, cv2_image)

        print(f"📸 Frame guardado en {filename}")
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
        self.recognizer = KaldiRecognizer(VOSK_MODEL, SAMPLE_RATE)
        
        # 📂 Crear archivo temporal para depuración de audio
        self.temp_audio_path = os.path.join(tempfile.gettempdir(), "debug_audio.wav")
        self.wav_file = wave.open(self.temp_audio_path, "wb")
        self.wav_file.setnchannels(1)  # Mono
        self.wav_file.setsampwidth(2)  # 16 bits
        self.wav_file.setframerate(SAMPLE_RATE)

        print(f"🎙️ Grabando audio recibido en: {self.temp_audio_path}")
        
        # Ejecutar bucle asíncrono para escuchar voz
        asyncio.ensure_future(self._run_loop())

    async def _run_loop(self):
        """Consume audio continuamente y detecta comandos de voz."""
        print("🎧 Iniciando procesamiento continuo de audio...")
        audio_buffer = bytearray()

        while not self.stop_event.is_set():
            try:
                frame = await self.track.recv()

                if frame.pts == self.last_pts:
                    continue
                self.last_pts = frame.pts

                # Convertir el frame de audio
                chunk = frame.to_ndarray(format="s16")
                audio_data = chunk.tobytes()
                self.wav_file.writeframes(audio_data)
                
                audio_buffer.extend(audio_data)

                # Procesar cada ~0.5 segundos de audio
                if len(audio_buffer) >= int(SAMPLE_RATE * 2 * 0.5):
                    buffer_to_process = bytes(audio_buffer)
                    if self.recognizer.AcceptWaveform(buffer_to_process):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "").strip().lower()
                        if text:
                            print(f"🗣️ Comando detectado: {text}")
                            await self._process_command(text)
                        audio_buffer.clear()
                    else:
                        partial = json.loads(self.recognizer.PartialResult())
                        partial_text = partial.get("partial", "").strip().lower()
                        if partial_text:
                            print(f"🗣️ Parcial: {partial_text}")

            except MediaStreamError:
                print("🔚 Fin del stream de audio.")
                break
            except Exception as e:
                print(f"⚠️ Error crítico en el loop de audio: {e}")
                await asyncio.sleep(0.1)

        print("🎧 AudioProcessorTrack: Loop de consumo de audio finalizado.")
        self.wav_file.close()
        print(f"🎙️ Archivo de depuración guardado en: {self.temp_audio_path}")

    def stop(self):
        """Detiene el bucle de audio."""
        self.stop_event.set()

    async def _process_command(self, command):
        """Decide qué hacer con el comando de voz."""
        
        if any(keyword in command for keyword in ["tomar foto", "capturar", "saca foto", "fotografía"]):
            print("📸 Comando de captura detectado.")
            captured_image_path = await self.video_processor.capture_frame()
            if captured_image_path:
                await self.sio.emit("command_executed", {
                    "action": "photo_captured",
                    "path": captured_image_path
                })
                
        # Puedes añadir más comandos aquí (ej. iniciar grabación, detener, etc.)
        elif "iniciar grabación" in command:
            print("🎬 Comando 'Iniciar Grabación' detectado.")
            await self.sio.emit("command_executed", {"action": "start_recording"})
        
        else:
            print(f"❓ Comando no reconocido: {command}")
            await self.sio.emit("command_executed", {"action": "command_not_recognized", "command": command})
            
    async def recv(self):
        """Método requerido por MediaStreamTrack, no usado aquí."""
        await asyncio.sleep(0.01)
        return None