import cv2
from aiortc import VideoStreamTrack

class VideoProcessorTrack(VideoStreamTrack):
    def __init__(self, track):
        super().__init__()
        self.track = track

    async def recv(self):
        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cv2.imshow("Procesado", gray)
        cv2.waitKey(1)

        return frame
