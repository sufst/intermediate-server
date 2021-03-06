import asyncio
import json
import threading
import unittest

import websockets

import server


class ServerThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.loop = asyncio.new_event_loop()
        self.running = False

    def run(self):
        self.running = True
        asyncio.set_event_loop(self.loop)
        server.Server("127.0.0.1", 19900, "COM0", 115200, "FFFFFFFFFFFFFFFF", "INFO").run()

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.join()
        self.running = False


async def _test_request():
    async with websockets.connect("ws://localhost:8765") as websocket:
        await websocket.send("GET /sensors?amount=10")

        response_json = await websocket.recv()
        response = json.loads(response_json)

        print(response)

        await websocket.close()


class TestServerRestful(unittest.TestCase):
    def test_restful(self):
        ser_thread = ServerThread()
        ser_thread.start()

        asyncio.get_event_loop().run_until_complete(_test_request())
        ser_thread.stop()
