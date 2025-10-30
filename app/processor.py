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
import numpy as np
from av import AudioResampler

MODEL_PATH = "/usr/local/lib/python3.11/site-packages/vosk_model/vosk-model-small-es-0.42"
print(f"DEBUG: ¿Existe el modelo? {os.path.isdir(MODEL_PATH)}")

# Vosk requiere específicamente 16kHz
VOSK_SAMPLE_RATE = 16000

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
        
        # CRÍTICO: Inicializar el recognizer con la tasa correcta
        self.recognizer = KaldiRecognizer(VOSK_MODEL, VOSK_SAMPLE_RATE)
        self.recognizer.SetWords(True)  # Obtener palabras individuales
        
        # Resampler para convertir audio a 16kHz mono
        self.resampler = None
        self.input_sample_rate = None
        
        # Buffer de audio acumulado
        self.audio_buffer = bytearray()
        
        # 📂 Crear archivo temporal para depuración
        self.temp_audio_path = os.path.join(tempfile.gettempdir(), "debug_audio.wav")
        self.wav_file = wave.open(self.temp_audio_path, "wb")
        self.wav_file.setnchannels(1)  # Mono
        self.wav_file.setsampwidth(2)  # 16 bits
        self.wav_file.setframerate(VOSK_SAMPLE_RATE)

        print(f"🎙️ Grabando audio recibido en: {self.temp_audio_path}")
        
        # Ejecutar bucle asíncrono
        asyncio.ensure_future(self._run_loop())

    def _resample_audio(self, frame):
        """Resamplea el audio a 16kHz mono si es necesario."""
        # Detectar la tasa de muestreo de entrada
        if self.input_sample_rate is None:
            self.input_sample_rate = frame.sample_rate
            num_channels = frame.layout.channels
            channel_names = [str(ch) for ch in frame.layout.channels]
            print(f"🎵 Tasa de muestreo detectada: {self.input_sample_rate}Hz")
            print(f"🎵 Canales detectados: {len(channel_names)} - {channel_names}")
            
            # Si no es 16kHz mono, crear resampler
            if self.input_sample_rate != VOSK_SAMPLE_RATE or len(channel_names) != 1:
                self.resampler = AudioResampler(
                    format='s16',
                    layout='mono',
                    rate=VOSK_SAMPLE_RATE
                )
                print(f"🔄 Resampler creado: {self.input_sample_rate}Hz ({len(channel_names)} canales) → {VOSK_SAMPLE_RATE}Hz (1 canal)")
            else:
                print(f"✅ Audio ya está en formato correcto: {VOSK_SAMPLE_RATE}Hz mono")
        
        # Aplicar resampling si es necesario
        if self.resampler:
            try:
                resampled_frames = self.resampler.resample(frame)
                if resampled_frames and len(resampled_frames) > 0:
                    resampled = resampled_frames[0]
                    # Debug del primer frame procesado
                    if not hasattr(self, '_first_resample_done'):
                        self._first_resample_done = True
                        arr = resampled.to_ndarray()
                        print(f"✅ Primer frame resampled exitosamente:")
                        print(f"   - Shape: {arr.shape}")
                        print(f"   - Dtype: {arr.dtype}")
                        print(f"   - Sample rate: {resampled.sample_rate}Hz")
                        print(f"   - Canales: {len(resampled.layout.channels)}")
                    return resampled
                else:
                    if not hasattr(self, '_empty_warning_shown'):
                        self._empty_warning_shown = True
                        print("⚠️ Resampler retornó frames vacíos")
                    return None
            except Exception as e:
                if not hasattr(self, '_resample_error_shown'):
                    self._resample_error_shown = True
                    print(f"⚠️ Error en resampling: {e}")
                    import traceback
                    traceback.print_exc()
                return None
        
        return frame

    async def _run_loop(self):
        """Consume audio continuamente y detecta comandos de voz."""
        print("🎧 Iniciando procesamiento continuo de audio...")
        
        # Umbral de buffer: ~0.3 segundos de audio
        buffer_threshold = int(VOSK_SAMPLE_RATE * 2 * 0.3)
        frame_count = 0

        while not self.stop_event.is_set():
            try:
                frame = await self.track.recv()

                # Evitar frames duplicados
                if frame.pts == self.last_pts:
                    continue
                self.last_pts = frame.pts
                frame_count += 1

                # Resamplear el audio a 16kHz mono
                resampled_frame = self._resample_audio(frame)
                if resampled_frame is None:
                    continue

                # Convertir a bytes
                chunk = resampled_frame.to_ndarray()
                
                if len(chunk.shape) > 1:
                    # Si es (1, N), aplanar a (N,)
                    if chunk.shape[0] == 1:
                        chunk = chunk.flatten()
                    elif chunk.shape[1] > 1:
                        chunk = chunk.mean(axis=1).astype(np.int16)
                    else:
                        chunk = chunk.flatten()
                
                if chunk.dtype != np.int16:
                    chunk = chunk.astype(np.int16)
                
                audio_data = chunk.tobytes()
                
                # Debug cada 100 frames
                if frame_count % 100 == 0:
                    print(f"🎤 Frame {frame_count}: {len(audio_data)} bytes, shape después de procesar: {chunk.shape}, min={chunk.min()}, max={chunk.max()}")
                
                # Guardar para depuración
                self.wav_file.writeframes(audio_data)
                
                # Acumular en buffer
                self.audio_buffer.extend(audio_data)

                # Procesar cuando tengamos suficiente audio
                if len(self.audio_buffer) >= buffer_threshold:
                    buffer_to_process = bytes(self.audio_buffer)
                    
                    # Enviar al recognizer
                    if self.recognizer.AcceptWaveform(buffer_to_process):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "").strip().lower()
                        if text:
                            print(f"🗣️ TEXTO FINAL: '{text}'")
                            await self._process_command(text)
                    else:
                        # Resultado parcial
                        partial = json.loads(self.recognizer.PartialResult())
                        partial_text = partial.get("partial", "").strip().lower()
                        if partial_text:
                            print(f"🗣️ Parcial: '{partial_text}'")
                    
                    # Limpiar buffer después de procesar
                    self.audio_buffer.clear()

            except MediaStreamError:
                print("🔚 Fin del stream de audio.")
                break
            except Exception as e:
                print(f"⚠️ Error en el loop de audio: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(0.1)

        # Procesar audio residual
        if self.audio_buffer:
            self.recognizer.AcceptWaveform(bytes(self.audio_buffer))
            final_result = json.loads(self.recognizer.FinalResult())
            text = final_result.get("text", "").strip().lower()
            if text:
                print(f"🗣️ TEXTO FINAL (residual): '{text}'")
                await self._process_command(text)

        print(f"🎧 AudioProcessorTrack: Loop finalizado. Total frames procesados: {frame_count}")
        self.wav_file.close()
        print(f"🎙️ Archivo de depuración guardado en: {self.temp_audio_path}")


    def stop(self):
        """Detiene el bucle de audio."""
        self.stop_event.set()

    async def _process_command(self, command):
        """Procesa comandos de voz detectados."""
        
        # Comandos de captura de foto
        if any(keyword in command for keyword in ["tomar foto", "capturar", "saca foto", "fotografía", "foto"]):
            print("📸 Comando de captura detectado.")
            captured_image_path = await self.video_processor.capture_frame()
            if captured_image_path:
                await self.sio.emit("command_executed", {
                    "action": "photo_captured",
                    "path": captured_image_path
                })
        
        # Comando de iniciar grabación
        elif any(keyword in command for keyword in ["iniciar grabación", "empezar a grabar", "comenzar grabación"]):
            print("🎬 Comando 'Iniciar Grabación' detectado.")
            await self.sio.emit("command_executed", {"action": "start_recording"})
        
        # Comando de detener grabación
        elif any(keyword in command for keyword in ["detener grabación", "parar grabación", "terminar grabación"]):
            print("⏹️ Comando 'Detener Grabación' detectado.")
            await self.sio.emit("command_executed", {"action": "stop_recording"})
        
        else:
            print(f"❓ Comando no reconocido: '{command}'")
            await self.sio.emit("command_executed", {
                "action": "command_not_recognized", 
                "command": command
            })

    async def recv(self):
        """Método requerido por MediaStreamTrack, no usado aquí."""
        await asyncio.sleep(0.01)
        return None