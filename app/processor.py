import cv2
from aiortc import VideoStreamTrack

class VideoProcessorTrack(VideoStreamTrack):
    def __init__(self, track):
        super().__init__()
        self.track = track
        self.count = 0

    async def recv(self):
        print("📹 Stream de video processor track")
        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        self.count += 1
        if self.count % 30 == 0:
            path = f"/tmp/frame_{self.count}.jpg"
            cv2.imwrite(path, gray)
            print(f"🖼️ Frame guardado en {path}")

        return frame
