import asyncio
from .signaling import sio, register_signaling_events

async def main():
    register_signaling_events()
    await sio.connect("http://host.docker.internal:3000")
    await sio.wait()

if __name__ == "__main__":
    asyncio.run(main())
